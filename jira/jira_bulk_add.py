import json
import requests
from requests.auth import HTTPBasicAuth
from config import (
    JIRA_BASE_URL,
    JIRA_USERNAME,
    JIRA_API_TOKEN,
    JIRA_ASSIGNEE_ACCOUNT_ID,
    JIRA_PROJECT_ID,
    JIRA_ISSUE_TYPE_ID,
    ISSUES_FILE_PATH
)

jira_url = f"{JIRA_BASE_URL}/rest/api/3/issue/"

auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)

headers = {"Accept": "application/json", "Content-Type": "application/json"}

payload_json = {
    "fields": {
        "summary": "Automate version check and upgrade alias",
        "assignee": {"accountId": JIRA_ASSIGNEE_ACCOUNT_ID},
        "description": {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Git Watch enabled"}
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Check running"}
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Check git release"}
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Upgrade alias"}
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Status check alias"}
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        },
        "issuetype": {"id": JIRA_ISSUE_TYPE_ID},
        "labels": ["IT", "Development", "SysAdmin"],
        "project": {"id": JIRA_PROJECT_ID},
    }
}

issues_file = open(ISSUES_FILE_PATH, "r")
lines = issues_file.readlines()

for line in lines:
    issue_desc = line.strip()
    payload_json["fields"][
        "summary"
    ] = f"Automate version check and upgrade - {issue_desc}"
    payload = json.dumps(payload_json)
    # print(line.strip())
    print(payload_json["fields"]["summary"])
    response = requests.request(
        "POST", jira_url, data=payload, headers=headers, auth=auth
    )
    print(
        json.dumps(
            json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")
        )
    )

# Check the response
# if response.status_code == 201:
#     print("Issue created successfully.")
#     print("Issue Key:", response.json()["key"])
# else:
#     print(f"Failed to create issue. Status code: {response.status_code}")
#     print("Response:", response.text)
