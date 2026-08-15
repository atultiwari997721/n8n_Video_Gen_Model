import os
import json
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.database import get_db, User
from src.main import run_pipeline
from src.github_bot import run_github_bot

app = FastAPI()

# Allow HTTP for local testing of OAuth
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Make sure templates folder exists
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

templates = Jinja2Templates(directory=templates_dir)

# Vercel forces us to read the client_secrets from the environment or a bundled file.
# For local dev, we use the file.
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_secrets.json")

def get_oauth_flow(request: Request):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    # Build dynamic redirect URI based on the incoming request
    # If request is HTTPS or running on Render, ensure the scheme is https
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    redirect_uri = f"{scheme}://{request.url.netloc}/oauth2callback"
    
    if client_id and client_secret:
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=['https://www.googleapis.com/auth/youtube.upload'],
            redirect_uri=redirect_uri
        )
        return flow
    elif os.path.exists(CLIENT_SECRETS_FILE):
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=['https://www.googleapis.com/auth/youtube.upload'],
            redirect_uri=redirect_uri
        )
        return flow
    return None

global_flow_store = {}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

class UserData(BaseModel):
    session_id: str
    gemini_key: str = ""
    github_pat: str = ""

@app.post("/api/user/save")
async def save_user(data: UserData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == data.session_id).first()
    if not user:
        user = User(session_id=data.session_id)
        db.add(user)
    
    if data.gemini_key: user.gemini_key = data.gemini_key
    if data.github_pat: user.github_pat = data.github_pat
    db.commit()
    return {"status": "success"}

@app.get("/api/user/{session_id}")
async def get_user(session_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user:
        return {"youtube_connected": False, "gemini_key": "", "github_pat": ""}
    return {
        "youtube_connected": bool(user.youtube_token),
        "gemini_key": user.gemini_key or "",
        "github_pat": user.github_pat or ""
    }

@app.get("/login")
async def login(request: Request, session_id: str):
    flow = get_oauth_flow(request)
    if not flow:
        return RedirectResponse(url="/?error=Missing+Google+OAuth+Credentials")
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    global_flow_store[state] = {'flow': flow, 'session_id': session_id}
    return RedirectResponse(url=authorization_url)

@app.get("/oauth2callback")
async def oauth2callback(request: Request, db: Session = Depends(get_db)):
    state = request.query_params.get("state")
    store = global_flow_store.get(state)
    
    if not store:
        return RedirectResponse(url="/?error=Flow+state+not+found")
        
    flow = store['flow']
    session_id = store['session_id']
    
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    creds_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user:
        user = User(session_id=session_id)
        db.add(user)
        
    user.youtube_token = json.dumps(creds_data)
    db.commit()
    
    return RedirectResponse(url="/")

@app.get("/api/trigger/youtube")
async def trigger_youtube(session_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user or not user.gemini_key or not user.youtube_token:
        return JSONResponse(status_code=400, content={"message": "Missing API keys or YouTube connection."})
    
    # In Vercel, this would trigger a GitHub Action. For local simulation, we run it directly.
    # Note: If deployed on Vercel, this function will timeout if it takes >10s.
    try:
        run_pipeline(api_key=user.gemini_key, youtube_token_json=user.youtube_token)
        return {"message": "YouTube Video Generated & Uploaded successfully!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Pipeline failed: {str(e)}"})

@app.get("/api/trigger/github")
async def trigger_github(session_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user or not user.gemini_key or not user.github_pat:
        return JSONResponse(status_code=400, content={"message": "Missing Gemini or GitHub API keys."})
    
    try:
        run_github_bot(api_key=user.gemini_key, github_pat=user.github_pat)
        return {"message": "GitHub problem pushed successfully!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"GitHub bot failed: {str(e)}"})

# --- VERCEL CRON JOBS ---

@app.get("/api/cron/github")
async def cron_github(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.gemini_key != None, User.github_pat != None).all()
    count = 0
    for user in users:
        try:
            run_github_bot(api_key=user.gemini_key, github_pat=user.github_pat)
            count += 1
        except:
            pass
    return {"message": f"Ran GitHub bot for {count} users"}

@app.get("/api/cron/youtube")
async def cron_youtube(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.gemini_key != None, User.youtube_token != None).all()
    count = 0
    for user in users:
        try:
            run_pipeline(api_key=user.gemini_key, youtube_token_json=user.youtube_token)
            count += 1
        except:
            pass
    return {"message": f"Ran YouTube pipeline for {count} users"}
