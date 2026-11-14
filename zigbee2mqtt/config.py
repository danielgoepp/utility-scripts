import os
from dotenv import load_dotenv

load_dotenv()

# MQTT Configuration
MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "mqtt_client")

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")

# File paths
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", "/tmp/state.json")

# Zigbee2MQTT data directories
Z2M_BASE_PATH = os.getenv("Z2M_BASE_PATH", "/Volumes/k3s-prod-data/zigbee2mqtt")
Z2M_INSTANCES = os.getenv("Z2M_INSTANCES", "11,15").split(",")

# Monitoring timeout
Z2M_TIMEOUT = int(os.getenv("Z2M_TIMEOUT", "5"))

# Uptime Kuma: one instance, one Push monitor (token) per bridge, e.g.
# UPTIME_KUMA_PUSH_TOKEN_ZIGBEE15=<token>
UPTIME_KUMA_URL = os.getenv("UPTIME_KUMA_URL")


def uptime_kuma_push_url(bridge):
    token = os.getenv(f"UPTIME_KUMA_PUSH_TOKEN_{bridge.upper()}")
    return f"{UPTIME_KUMA_URL}/api/push/{token}" if UPTIME_KUMA_URL and token else None
