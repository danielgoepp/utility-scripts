import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

OPNSENSE_URL = os.getenv("OPNSENSE_URL")
OPNSENSE_API_KEY = os.getenv("OPNSENSE_API_KEY")
OPNSENSE_API_SECRET = os.getenv("OPNSENSE_API_SECRET")
OPNSENSE_VERIFY_SSL = os.getenv("OPNSENSE_VERIFY_SSL", "true").lower() not in ("false", "0", "no")
