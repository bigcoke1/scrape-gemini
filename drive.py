import os
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRETS_FILE = "credentials.json"

def get_credentials(username):
    """Fetches credentials for a specific user."""
    token_path = f'tokens/token_{username}.json'
    if not os.path.exists(token_path):
        return redirect(url_for('login', param1=token_path))

    with open(token_path, 'r') as token_file:
        creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
    return creds

def upload_file(chat_id, username, image):
    try:
        image_data = base64.b64decode(image)

        save_path = f'chart/{chat_id}.png'
        with open(save_path, "wb") as file:
            file.write(image_data)
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