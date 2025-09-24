import os
from dotenv import load_dotenv

load_dotenv()

# JIRA Configuration
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_ASSIGNEE_ACCOUNT_ID = os.getenv("JIRA_ASSIGNEE_ACCOUNT_ID")
JIRA_PROJECT_ID = os.getenv("JIRA_PROJECT_ID")
JIRA_ISSUE_TYPE_ID = os.getenv("JIRA_ISSUE_TYPE_ID")

# Epic IDs for spring maintenance
JIRA_EPIC_EQUIPMENT_ID = os.getenv("JIRA_EPIC_EQUIPMENT_ID")
JIRA_EPIC_OUTSIDE_ID = os.getenv("JIRA_EPIC_OUTSIDE_ID")
JIRA_EPIC_INSIDE_ID = os.getenv("JIRA_EPIC_INSIDE_ID")

# Account IDs for assignees
JIRA_DAN_ACCOUNT_ID = os.getenv("JIRA_DAN_ACCOUNT_ID")
JIRA_JEN_ACCOUNT_ID = os.getenv("JIRA_JEN_ACCOUNT_ID")

# File paths
ISSUES_FILE_PATH = os.getenv("ISSUES_FILE_PATH")
MAINTENANCE_EXCEL_PATH = os.getenv("MAINTENANCE_EXCEL_PATH")