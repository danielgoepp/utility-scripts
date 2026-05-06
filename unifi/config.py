import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

UNIFI_CONTROLLER = os.getenv("UNIFI_CONTROLLER")
USERNAME = os.getenv("UNIFI_USERNAME")
PASSWORD = os.getenv("UNIFI_PASSWORD")
SITE = os.getenv("UNIFI_SITE")
UNIFI_API_KEY = os.getenv("UNIFI_LOCAL_API_KEY")
