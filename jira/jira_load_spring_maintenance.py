import json
import requests
import pandas
from requests.auth import HTTPBasicAuth
from config import (
    JIRA_BASE_URL,
    JIRA_USERNAME,
    JIRA_API_TOKEN,
    JIRA_PROJECT_ID,
    JIRA_ISSUE_TYPE_ID,
    JIRA_EPIC_EQUIPMENT_ID,
    JIRA_EPIC_OUTSIDE_ID,
    JIRA_EPIC_INSIDE_ID,
    JIRA_DAN_ACCOUNT_ID,
    JIRA_JEN_ACCOUNT_ID,
    MAINTENANCE_EXCEL_PATH
)

jira_url = f"{JIRA_BASE_URL}/rest/api/3/"
auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)

headers = {"Accept": "application/json", "Content-Type": "application/json"}
epic_ids = {
    "Equipment": JIRA_EPIC_EQUIPMENT_ID,
    "Outside": JIRA_EPIC_OUTSIDE_ID,
    "Inside": JIRA_EPIC_INSIDE_ID
}
account_ids = {
    "Dan": JIRA_DAN_ACCOUNT_ID,
    "Jen": JIRA_JEN_ACCOUNT_ID,
}

maintenance = pandas.read_excel(MAINTENANCE_EXCEL_PATH)

for index, row in maintenance[
    maintenance["Schedule"].str.contains("Spring")
].iterrows():

    payload_json = {
        "fields": {
            "project": {"id": JIRA_PROJECT_ID},
            "issuetype": {"id": JIRA_ISSUE_TYPE_ID},
            "summary": row["Item"],
            "labels": row["Labels"].split(", "),
            "parent": {"id": epic_ids[row["Epic"]]},
            "timetracking": {"originalEstimate": row["Time"]},
        },
    }

    if isinstance(row["Assignee"], str):
        payload_json["fields"]["assignee"] = {"accountId": account_ids[row["Assignee"]]}

    print(json.dumps(payload_json))

    response = requests.request(
        "POST",
        jira_url + "issue/",
        data=json.dumps(payload_json),
        headers=headers,
        auth=auth,
    )

    print(
        json.dumps(
            json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")
        )
    )

    if response.status_code == 201:
        print("Issue created successfully.")
        print("Issue Key:", response.json()["key"])
    else:
        print(f"Failed to create issue. Status code: {response.status_code}")
        print("Response:", response.text)

    # break
