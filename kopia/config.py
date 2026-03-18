import os
from dotenv import load_dotenv

load_dotenv()

# Comma-separated list of instance names (e.g., "prod,dev,nas")
KOPIA_INSTANCES = [i.strip() for i in os.getenv("KOPIA_INSTANCES", "").split(",") if i.strip()]

# Maximum age (in hours) before a source's last snapshot is considered stale
KOPIA_MAX_SNAPSHOT_AGE_HOURS = int(os.getenv("KOPIA_MAX_SNAPSHOT_AGE_HOURS", "26"))

# TLS verification (set to "false" for self-signed certs)
KOPIA_VERIFY_TLS = os.getenv("KOPIA_VERIFY_TLS", "true").lower() != "false"

# Alertmanager integration (optional)
ALERTMANAGER_URL = os.getenv("ALERTMANAGER_URL")


def get_instance_config(name):
    """Load configuration for a named Kopia instance.

    Reads env vars prefixed with KOPIA_{NAME}_ (uppercase).
    """
    prefix = f"KOPIA_{name.upper()}_"
    return {
        "name": name,
        "server_url": os.getenv(f"{prefix}SERVER_URL"),
        "control_username": os.getenv(f"{prefix}CONTROL_USERNAME", "server-control"),
        "control_password": os.getenv(f"{prefix}CONTROL_PASSWORD"),
    }
