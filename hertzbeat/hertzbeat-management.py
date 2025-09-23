# For more information, see https://hertzbeat-prod.goepp.net/swagger-ui/index.html

import requests
import json
import pandas as pd
from config import HERTZBEAT_URL, HERTZBEAT_TOKEN


def get_monitors():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {HERTZBEAT_TOKEN}",
    }
    response = requests.get(f"{HERTZBEAT_URL}/api/monitors", headers=headers)
    response.raise_for_status()

    return response.json()["data"]["content"]


def create_monitor(monitor):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {HERTZBEAT_TOKEN}",
    }
    response = requests.post(
        f"{HERTZBEAT_URL}/api/monitor", headers=headers, json=monitor
    )
    print(json.dumps(response.json(), indent=2))
    response.raise_for_status()
    return response.json()


def load_monitors_from_excel():
    excel_file = "/Users/dang/Documents/Household/General/Information Technology.xlsx"
    sheet_name = "Synthetic Tests"
    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)

    monitor = {}
    for _, row in df.iterrows():
        # if row.get("type") == "ping":
        #     monitor = {
        #         "monitor": {
        #             "name": row.get("name"),
        #             "app": row.get("type"),
        #             "host": row.get("host"),
        #             "intervals": 60,
        #         },
        #         "params": [
        #             {"field": "timeout", "paramValue": 6000},
        #             {"field": "host", "paramValue": row.get("host")},
        #         ],
        #     }

        if row.get("type") == "http":  # and "pve" in str(row.get("name")).lower():
            if row.get("protocol") == "http":
                monitor = {
                    "monitor": {
                        "name": row.get("name"),
                        "app": "website",
                        "host": row.get("host"),
                        "intervals": 60,
                    },
                    "params": [
                        {"field": "timeout", "paramValue": 1000},
                        {"field": "host", "paramValue": row.get("host")},
                        {"field": "port", "paramValue": row.get("port")},
                        {
                            "field": "ssl",
                            "paramValue": (
                                False if row.get("protocol") == "http" else True
                            ),
                        },
                        {"field": "uri"},
                        {"field": "authType"},
                        {"field": "username"},
                        {"field": "password"},
                        {"field": "keyword"},
                    ],
                }
                print(json.dumps(monitor, indent=2))
                create_monitor(monitor)


if __name__ == "__main__":

    ## ===========================
    ## get monitors from hertzbeat
    ## ===========================

    # monitors = get_monitors()

    # dump entire monitor list as json
    # print(json.dumps(monitors, indent=2))

    # output each monitor in a list
    # for monitor in monitors:
    #     print(f"{monitor['name']},{monitor['host']},{monitor['app']}")
    #     print(json.dumps(monitor, indent=2))

    # output to a file
    # file = open("hertzbeat-maintenance.log", "w")
    # print(json.dump(monitors, file, indent=2))
    # file.close()

    # set_maintenance(monitors)

    ## ===========================
    ## load monitors from excel
    ## ===========================
    load_monitors_from_excel()
