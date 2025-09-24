#!/usr/bin/env python3

import requests
import config


headers = {
    "Authorization": f"Bearer {config.ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

response = requests.get(f"https://{config.HOST}/api/states", headers=headers)

if response.status_code == 200:
    devices = response.json()
    # filtered_devices = [
    #     device
    #     for device in devices
    #     if "device" in device["attributes"]
    #     and "lutron" in device["attributes"]["device"].get("identifiers", [[]])[0]
    # ]

    for device in devices:
        print(
            f"Entity ID: {device['entity_id']}, State: {device['state']}, Attributes: {device['attributes']}"
        )
else:
    print(f"Failed to retrieve devices, status code: {response.status_code}")
    print(response.text)
