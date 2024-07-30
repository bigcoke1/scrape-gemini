import os
import json
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_credentials(username):
    """Fetches credentials for a specific user."""
    token_file = f'token_{username}.json'
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            return creds

    # No valid credentials found, prompt user to login
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
    return creds

def upload_file(chat_id, username, image_url):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        save_path = f'chart/{chat_id}.png'
        with open(save_path, "wb") as file:
            file.write(response.content)
        print("Image successfully saved locally")

        creds = get_credentials(username)
        service = build('drive', 'v3', credentials=creds)

        # File to be uploaded
        file_metadata = {'name': f'{chat_id}_chart.png'}
        media = MediaFileUpload(save_path, mimetype='image/png')

        # Upload the file
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f'File ID: {file.get("id")}')

    except HttpError as error:
        print(f'An error occurred: {error}')