#!/usr/bin/env python3

import requests
import config


def ha_restart():
    try:
        print("Sending restart command to Home Assistant...")
        headers = {
            "Authorization": f"Bearer {config.ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"https://{config.HOST}/api/services/homeassistant/restart",
            headers=headers,
            data={},
        )

        if response.status_code == 200:
            print("✅ Restart command sent successfully!")
            print("Home Assistant is restarting... This may take a few minutes.")
            return True
        else:
            print(f"❌ Failed to restart. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending restart command: {e}")
        return False


if __name__ == "__main__":
    response = ha_restart()
