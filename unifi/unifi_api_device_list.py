import json
import requests
import config


def get_unifi_data():
    if not config.UNIFI_API_KEY:
        raise ValueError("UNIFI_API_KEY environment variable is required")

    headers = {
        "X-API-KEY": config.UNIFI_API_KEY,
        "Accept": "application/json",
    }

    try:
        # Get all the hosts (ui-protect and ui-network)
        hosts_response = requests.get("https://api.ui.com/v1/hosts", headers=headers)
        hosts_response.raise_for_status()
        
        # Get all the unifi devices (but not devices on the network)
        devices_response = requests.get("https://api.ui.com/v1/devices", headers=headers)
        devices_response.raise_for_status()
        
        return {
            "hosts": hosts_response.json(),
            "devices": devices_response.json()
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching UniFi data: {e}")
        return None


def main():
    data = get_unifi_data()
    if data:
        print(json.dumps(data, indent=4))


if __name__ == "__main__":
    main()
