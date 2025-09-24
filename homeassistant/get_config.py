#!/usr/bin/env python3

import json
import requests
import config


def call_api(endpoint, method="get"):
    headers = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    url = f"https://{config.HOST}/api/{endpoint}"

    if method == "get":
        response = requests.get(url, headers=headers)
        print(response)
        # print (json.dumps(response.text))
    elif method == "post":
        response = requests.post(url, headers=headers, data=json.dumps(data))
    else:
        raise ValueError("Invalid HTTP method")

    return response


def get_config():
    response = call_api("config")
    return response


# automation_entity_id = 'automation.your_automation_entity_id'

# Disable the specified automation
# ha_api.disable_automation(automation_entity_id)
ha_response = get_config()

# print(f"Automation {automation_entity_id} disabled.")
print(ha_response.text)
