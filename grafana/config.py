import os
from dotenv import load_dotenv

load_dotenv()

GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")
GRAFANA_URL = os.getenv("GRAFANA_URL")
