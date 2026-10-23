import os
from dotenv import load_dotenv

load_dotenv()

# Absolute path to the Obsidian note that lists installed applications
INSTALLED_APPS_NOTE = os.getenv("INSTALLED_APPS_NOTE")
