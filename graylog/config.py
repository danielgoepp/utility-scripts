import os
from dotenv import load_dotenv

load_dotenv()

GRAYLOG_API_URL = os.getenv("GRAYLOG_API_URL")
GRAYLOG_USERNAME = os.getenv("GRAYLOG_USERNAME")
GRAYLOG_PASSWORD = os.getenv("GRAYLOG_PASSWORD")
