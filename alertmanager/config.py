import os
from dotenv import load_dotenv

load_dotenv()

ALERTMANAGER_API_URL = os.getenv("ALERTMANAGER_API_URL")
ALERTMANAGER_CREATED_BY = os.getenv("ALERTMANAGER_CREATED_BY")
