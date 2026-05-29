import os
import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Scopes required for Drive upload
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_token():
    # This script assumes you have 'client_secret.json' in the same folder
    if not os.path.exists('client_secret.json'):
        print("Error: 'client_secret.json' not found! Please download it from Google Cloud Console.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    # This will open your web browser
    creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("\nSUCCESS! 'token.json' has been created.")
    print("Now upload 'token.json' to your server and point the Odoo module to it.")

if __name__ == '__main__':
    get_token()
