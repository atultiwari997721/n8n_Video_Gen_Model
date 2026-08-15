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

def upload_video(video_path: str, title: str, description: str, token_file: str = 'token.json'):
    """
    Uploads a video to YouTube.
    """
    print(f"Starting upload for {video_path}...")
    youtube = authenticate_youtube(token_file)

    # YouTube metadata
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

    print("Uploading video to YouTube (direct upload)...")
    try:
        response = request.execute()
        print(f"Upload Complete! Video ID: {response.get('id')}")
        print(f"Video URL: https://youtu.be/{response.get('id')}")
        return response.get('id')
    except Exception as e:
        import traceback
        print(f"ERROR details during upload: {str(e)}")
        if hasattr(e, 'content'):
            print(f"Response content: {e.content}")
        if hasattr(e, 'resp'):
            print(f"Response headers: {e.resp}")
        print(traceback.format_exc())
        raise e

if __name__ == "__main__":
    # Test upload (make sure to use a test video and private status!)
    # upload_video("final_short.mp4", "Test Title", "Test Description #shorts")
    pass
