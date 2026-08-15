import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def authenticate_youtube(token_file='token.json'):
    """
    Authenticates with YouTube using the given token file.
    """
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception(f"Valid {token_file} not found. Please authenticate via the web dashboard.")
            
    return build('youtube', 'v3', credentials=creds)

def upload_video(video_path: str, title: str, description: str, token_file: str = "token.json", callback=print):
    """
    Uploads a video to YouTube using the provided token file.
    """
    callback("Initializing YouTube upload...")
    
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            callback("Refreshing expired YouTube credentials...")
            creds.refresh(Request())
        else:
            callback("ERROR: Valid YouTube credentials not found.")
            return None

    youtube = build('youtube', 'v3', credentials=creds)

    title = title if len(title) <= 100 else title[:97] + "..."

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['shorts', 'motivation', 'mindset', 'success', 'quotes'],
            'categoryId': '27' # Education
        },
        'status': {
            'privacyStatus': 'public', # Set to 'private' or 'unlisted' for testing if desired
            'selfDeclaredMadeForKids': False
        }
    }

    # Upload configuration - use direct upload instead of resumable to avoid chunking/proxy errors on free hosting
    media = MediaFileUpload(
        video_path,
        mimetype='video/mp4',
        resumable=False
    )

    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    callback("Uploading video to YouTube (direct upload)...")
    try:
        response = request.execute()
        callback(f"Upload Complete! Video ID: {response.get('id')}")
        callback(f"Video URL: https://youtu.be/{response.get('id')}")
        return response.get('id')
    except Exception as e:
        import traceback
        callback(f"ERROR details during upload: {str(e)}")
        if hasattr(e, 'content'):
            callback(f"Response content: {e.content}")
        if hasattr(e, 'resp'):
            callback(f"Response headers: {e.resp}")
        callback(traceback.format_exc())
        raise e

if __name__ == "__main__":
    # Test upload (make sure to use a test video and private status!)
    # upload_video("final_short.mp4", "Test Title", "Test Description #shorts")
    pass
