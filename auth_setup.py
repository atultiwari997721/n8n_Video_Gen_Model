import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    """Shows basic usage of the YouTube Data API.
    Handles the initial OAuth 2.0 flow and saves the credentials to token.json.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing access token...")
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                print("Error: client_secrets.json not found.")
                print("Please download it from the Google Cloud Console and place it in this directory.")
                return

            print("Starting local server for authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful! token.json has been created.")
            print("Remember to NOT commit token.json or client_secrets.json to your repository.")
            print("Copy the contents of token.json into the YOUTUBE_TOKEN_JSON GitHub Secret.")

if __name__ == '__main__':
    main()
