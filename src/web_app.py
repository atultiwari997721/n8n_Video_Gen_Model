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

def get_oauth_flow(request: Request, session_id: str, db: Session):
    user = db.query(User).filter(User.session_id == session_id).first()
    client_id = user.google_client_id if user else None
    client_secret = user.google_client_secret if user else None
    
    # Fallback to server env vars if user hasn't provided their own
    if not client_id or not client_secret:
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    # Build dynamic redirect URI based on the incoming request
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
    google_client_id: str = ""
    google_client_secret: str = ""
    youtube_enabled: bool = False
    youtube_hour: int = 1440
    github_enabled: bool = False
    github_hour: int = 1440

@app.post("/api/user/save")
async def save_user(data: UserData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == data.session_id).first()
    if not user:
        user = User(session_id=data.session_id)
        db.add(user)
    
    if data.gemini_key: user.gemini_key = data.gemini_key
    if data.github_pat: user.github_pat = data.github_pat
    if data.google_client_id: user.google_client_id = data.google_client_id
    if data.google_client_secret: user.google_client_secret = data.google_client_secret
    
    user.youtube_enabled = data.youtube_enabled
    user.youtube_hour = data.youtube_hour
    user.github_enabled = data.github_enabled
    user.github_hour = data.github_hour
    
    db.commit()
    return {"status": "success"}

@app.get("/api/user/{session_id}")
async def get_user(session_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user:
        return {"youtube_connected": False, "gemini_key": "", "github_pat": "", "google_client_id": "", "google_client_secret": "", "youtube_enabled": False, "youtube_hour": 1440, "github_enabled": False, "github_hour": 1440}
        
    yt_hr = user.youtube_hour if user.youtube_hour is not None else 1440
    if yt_hr not in [1, 15, 60, 240, 720, 1440]:
        yt_hr = 1440
        
    gh_hr = user.github_hour if user.github_hour is not None else 1440
    if gh_hr not in [1, 15, 60, 240, 720, 1440]:
        gh_hr = 1440
        
    return {
        "youtube_connected": bool(user.youtube_token),
        "gemini_key": user.gemini_key or "",
        "github_pat": user.github_pat or "",
        "google_client_id": user.google_client_id or "",
        "google_client_secret": user.google_client_secret or "",
        "youtube_enabled": user.youtube_enabled or False,
        "youtube_hour": yt_hr,
        "github_enabled": user.github_enabled or False,
        "github_hour": gh_hr
    }

@app.get("/login")
async def login(request: Request, session_id: str, db: Session = Depends(get_db)):
    flow = get_oauth_flow(request, session_id, db)
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

from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
import queue
import threading
from src.database import ActivityLog, SessionLocal
from datetime import datetime

def run_and_log_youtube(session_id: str, gemini_key: str, youtube_token: str, callback=print, custom_topic: str = None, is_exact: bool = False):
    db = SessionLocal()
    try:
        url = run_pipeline(api_key=gemini_key, youtube_token_json=youtube_token, callback=callback, custom_topic=custom_topic, is_exact=is_exact)
        log = ActivityLog(session_id=session_id, service="youtube", status="success", message="Video Generated & Uploaded", link=url, timestamp=datetime.utcnow().isoformat())
        db.add(log)
        db.commit()
    except Exception as e:
        log = ActivityLog(session_id=session_id, service="youtube", status="error", message=f"Pipeline failed: {str(e)}", timestamp=datetime.utcnow().isoformat())
        db.add(log)
        db.commit()
    finally:
        db.close()

def run_and_log_github(session_id: str, gemini_key: str, github_pat: str, callback=print):
    db = SessionLocal()
    try:
        url = run_github_bot(api_key=gemini_key, github_pat=github_pat, callback=callback)
        log = ActivityLog(session_id=session_id, service="github", status="success", message="Daily Problem Pushed", link=url, timestamp=datetime.utcnow().isoformat())
        db.add(log)
        db.commit()
    except Exception as e:
        log = ActivityLog(session_id=session_id, service="github", status="error", message=f"GitHub Bot failed: {str(e)}", timestamp=datetime.utcnow().isoformat())
        db.add(log)
        db.commit()
    finally:
        db.close()

@app.get("/api/trigger/youtube")
async def trigger_youtube(session_id: str, topic: str = None, is_exact: bool = False, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user or not user.gemini_key or not user.youtube_token:
        return JSONResponse(status_code=400, content={"message": "Missing API keys or YouTube connection."})
    
    q = queue.Queue()
    
    def callback(msg):
        q.put(msg)
        
    def worker():
        try:
            run_and_log_youtube(user.session_id, user.gemini_key, user.youtube_token, callback=callback, custom_topic=topic, is_exact=is_exact)
            callback("DONE")
        except Exception as e:
            callback(f"ERROR: {e}")
            callback("DONE")
            
    threading.Thread(target=worker).start()
    
    def event_stream():
        while True:
            msg = q.get()
            if msg == "DONE":
                break
            # Convert newlines to breaks to not mess up SSE formatting
            safe_msg = str(msg).replace('\n', '<br>')
            yield f"data: {safe_msg}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/trigger/github")
async def trigger_github(session_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user or not user.gemini_key or not user.github_pat:
        return JSONResponse(status_code=400, content={"message": "Missing Gemini or GitHub API keys."})
    
    q = queue.Queue()
    
    def callback(msg):
        q.put(msg)
        
    def worker():
        try:
            run_and_log_github(user.session_id, user.gemini_key, user.github_pat, callback=callback)
            callback("DONE")
        except Exception as e:
            callback(f"ERROR: {e}")
            callback("DONE")
            
    threading.Thread(target=worker).start()
    
    def event_stream():
        while True:
            msg = q.get()
            if msg == "DONE":
                break
            safe_msg = str(msg).replace('\n', '<br>')
            yield f"data: {safe_msg}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# --- VERCEL/RENDER CRON JOBS ---

@app.get("/api/cron/tick")
async def cron_tick(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Master Heartbeat Endpoint for scheduling.
    Intended to be pinged exactly once per minute by an external service (e.g., cron-job.org).
    """
    import time
    current_minute_unix = int(time.time() / 60)
    
    # Process GitHub
    github_users = db.query(User).filter(
        User.gemini_key != None, 
        User.github_pat != None, 
        User.github_enabled == True
    ).all()
    
    queued_github = 0
    for user in github_users:
        interval = user.github_hour if user.github_hour else 1440
        if current_minute_unix % interval == 0:
            background_tasks.add_task(run_and_log_github, user.session_id, user.gemini_key, user.github_pat)
            queued_github += 1
        
    # Process YouTube
    youtube_users = db.query(User).filter(
        User.gemini_key != None, 
        User.youtube_token != None,
        User.youtube_enabled == True
    ).all()
    
    queued_youtube = 0
    for user in youtube_users:
        interval = user.youtube_hour if user.youtube_hour else 1440
        if current_minute_unix % interval == 0:
            background_tasks.add_task(run_and_log_youtube, user.session_id, user.gemini_key, user.youtube_token)
            queued_youtube += 1
        
    return {
        "message": "Minute heartbeat processed successfully",
        "jobs_queued": {
            "github": queued_github,
            "youtube": queued_youtube
        },
        "current_minute_unix": current_minute_unix
    }

@app.get("/api/logs/{session_id}")
async def get_logs(session_id: str, db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).filter(ActivityLog.session_id == session_id).order_by(ActivityLog.id.desc()).limit(20).all()
    return [{
        "service": log.service,
        "status": log.status,
        "message": log.message,
        "link": log.link,
        "timestamp": log.timestamp
    } for log in logs]
