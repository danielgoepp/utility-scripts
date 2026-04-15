"""
Reusable Google OAuth2 helper.

Run this file directly to perform the initial OAuth login and generate token.json:
    source .venv/bin/activate
    python3 google/auth.py

After authentication, token.json is saved and reused by all other Google scripts.
To force re-authentication (e.g. to change scopes), delete token.json and rerun.
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from config import CREDENTIALS_FILE, TOKEN_FILE, SCOPES


def get_credentials() -> Credentials:
    """Load existing credentials or run the OAuth login flow."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())
        print(f"Credentials saved to {TOKEN_FILE}")

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Authentication successful.")
    print(f"Token stored at: {TOKEN_FILE}")
