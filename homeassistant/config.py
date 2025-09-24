import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("HOST")
TLS = os.getenv("TLS", "False").lower() == "true"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
