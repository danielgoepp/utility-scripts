import os
from dotenv import load_dotenv

load_dotenv()

HERTZBEAT_URL = os.getenv("HERTZBEAT_URL")
HERTZBEAT_TOKEN = os.getenv("HERTZBEAT_TOKEN")
