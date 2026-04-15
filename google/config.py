import os
from dotenv import load_dotenv

load_dotenv()

# Paths to OAuth credential files
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google/credentials.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "google/token.json")

# OAuth scopes — extend this list as more Google APIs are used
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
]
