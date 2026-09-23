import os
from dotenv import load_dotenv

load_dotenv()

# 1Password account to connect to via the desktop app (sign-in address or account name)
OP_ACCOUNT = os.getenv("OP_ACCOUNT")

# Comma-separated domains whose URLs (including subdomains) should be targeted
OP_AUTOFILL_DOMAINS = [d.strip().lower() for d in os.getenv("OP_AUTOFILL_DOMAINS", "").split(",") if d.strip()]
