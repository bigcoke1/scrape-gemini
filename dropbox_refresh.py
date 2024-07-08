import os
import requests
import time

TOKEN_URL = 'https://api.dropboxapi.com/oauth2/token'
AUTHORIZATION_URL = 'https://www.dropbox.com/oauth2/authorize'

client_id = "r0tcggx9o3zo5k4"
client_secret = os.environ["DROPBOX_SECRET"]

def initialize():
    authorization_params = {
        "response_type": "code",
        "client_id": client_id,
        "token_access_type": "offline"
    }

    auth_url = AUTHORIZATION_URL + "?" + "&".join([f'{key}={value}' for key, value in authorization_params.items()])

    print(auth_url)

    authorization_code = "_NfO0PWkac4AAAAAAAAAH94DvIDLXdT4BIF87QflwD8"

    token_params = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "client_id": client_id,
        "client_secret": client_secret
    }

    response = requests.post(TOKEN_URL, data=token_params)
    tokens = response.json()

    access_token = tokens['access_token']
    refresh_token = tokens.get('refresh_token')  # Only included if you requested 'token_access_type=offline'
    expires_in = tokens['expires_in']  # Time in seconds until the access token expires

    print(f'Access Token: {access_token}')
    if refresh_token:
        print(f'Refresh Token: {refresh_token}')
    print(f'Access Token expires in: {expires_in} seconds')

# Function to refresh the access token
def refresh_access_token():
    token_params = {
        'grant_type': 'refresh_token',
        'refresh_token': os.environ["REFRESH_TOKEN"],
        'client_id': client_id,
        'client_secret': client_secret,
    }

    try:
        response = requests.post(TOKEN_URL, data=token_params)
        response.raise_for_status()
        tokens = response.json()

        new_access_token = tokens['access_token']
        expires_in = tokens['expires_in']
        expires_at = time.time() + expires_in

        print(f'New Access Token: {new_access_token}')
        print(f'Access Token expires at: {time.ctime(expires_at)}')

        # Return the new access token and its expiration time
        return new_access_token, expires_at

    except requests.exceptions.HTTPError as e:
        print(f'Error refreshing access token: {e}')
        return None, None

# Example usage: Check if access token is expired and refresh if needed
def main():
    # Simulate checking if access token is expired (replace with your logic)
    current_access_token = os.environ["DROPBOX_API_KEY"]

    new_access_token, new_expires_at = refresh_access_token()

    # Use the new access token for API requests
    if new_access_token:
        current_access_token = new_access_token
    else:
        print('Failed to refresh access token.')

    # Example API request using the current_access_token
    # Replace with your actual API request logic
    api_url = 'https://api.dropboxapi.com/2/users/get_current_account'
    headers = {'Authorization': f'Bearer {current_access_token}'}

    try:
        response = requests.post(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print('User account information:')
        print(data)
    except requests.exceptions.HTTPError as e:
        print(f'Error making API request: {e}')

if __name__ == '__main__':
    main()
