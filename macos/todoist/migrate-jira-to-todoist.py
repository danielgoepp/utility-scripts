#!/usr/bin/env python3
"""Migrate Jira Cloud epic issues to Todoist inbox.

Fetches all issues from a specified Jira epic and creates corresponding
tasks in the Todoist inbox for manual sorting. No project assignment is
made automatically.

Setup:
    cp macos/.env.example macos/.env
    # Fill in JIRA_* and TODOIST_API_TOKEN
    source .venv/bin/activate
    pip install requests python-dotenv
    python3 macos/todoist/migrate-jira-sprint-to-todoist.py --list-epics --project PROJ
    python3 macos/todoist/migrate-jira-sprint-to-todoist.py --epic PROJ-123 --dry-run
    python3 macos/todoist/migrate-jira-sprint-to-todoist.py --epic PROJ-123
"""

import argparse
import os
import sys
import time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")

TODOIST_BASE_URL = "https://api.todoist.com/api/v1"


# ---------------------------------------------------------------------------
# Jira API helpers
# ---------------------------------------------------------------------------

def _jira_auth():
    return HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)



def _jira_api_post(path, body):
    url = f"{JIRA_BASE_URL}/rest/api/3{path}"
    resp = requests.post(
        url,
        auth=_jira_auth(),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def list_projects():
    """Return all projects accessible to the authenticated user."""
    projects = []
    start_at = 0
    max_results = 50
    while True:
        url = f"{JIRA_BASE_URL}/rest/api/3/project/search"
        resp = requests.get(
            url,
            auth=_jira_auth(),
            headers={"Accept": "application/json"},
            params={"startAt": start_at, "maxResults": max_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        projects.extend(data.get("values", []))
        if data.get("isLast", True):
            break
        start_at += max_results
    return projects


def list_epics(project_key):
    """Return all epics in a project."""
    epics = []
    next_page_token = None
    while True:
        body = {
            "jql": f"project = {project_key} AND issuetype = Epic AND status != Done ORDER BY created DESC",
            "maxResults": 50,
            "fields": ["summary", "status"],
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        data = _jira_api_post("/search/jql", body)
        epics.extend(data.get("issues", []))
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
    return epics


def get_epic_issues(epic_key):
    """Return all issues belonging to an epic (works for both classic and next-gen projects)."""
    issues = []
    next_page_token = None
    while True:
        body = {
            "jql": f'(parent = "{epic_key}" OR "Epic Link" = "{epic_key}") AND status != Done',
            "maxResults": 50,
            "fields": ["summary", "description"],
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        data = _jira_api_post("/search/jql", body)
        issues.extend(data.get("issues", []))
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
    return issues


# ---------------------------------------------------------------------------
# Todoist API helpers
# ---------------------------------------------------------------------------

def _todoist_headers():
    return {"Authorization": f"Bearer {TODOIST_API_TOKEN}"}


def create_task(content, description=None, dry_run=False):
    """Create a task in the Todoist inbox (no project_id = inbox)."""
    payload = {"content": content}
    if description:
        payload["description"] = description

    if dry_run:
        print(f"  [dry-run] Would create task: {content!r}")
        return "dry-run-task"

    resp = requests.post(
        f"{TODOIST_BASE_URL}/tasks",
        headers=_todoist_headers(),
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------

def issue_to_task_fields(issue):
    """Extract Todoist-relevant fields from a Jira issue."""
    fields = issue["fields"]
    content = fields.get("summary", "(no summary)")

    raw_desc = fields.get("description")
    description = None
    if raw_desc:
        if isinstance(raw_desc, str):
            description = raw_desc.strip() or None
        elif isinstance(raw_desc, dict):
            description = _adf_to_text(raw_desc).strip() or None

    return {"content": content, "description": description}


def _adf_to_text(node, depth=0):
    """Recursively extract plain text from an Atlassian Document Format node."""
    if depth > 20:
        return ""
    node_type = node.get("type", "")

    # Smart link cards store the URL in attrs.url, not in text
    if node_type in ("inlineCard", "blockCard", "embedCard"):
        return node.get("attrs", {}).get("url", "")

    text = node.get("text", "")
    children = node.get("content", [])
    parts = [text] if text else []
    for child in children:
        parts.append(_adf_to_text(child, depth + 1))
    joined = " ".join(p for p in parts if p)
    if node_type in ("paragraph", "heading", "bulletList", "orderedList", "listItem"):
        joined = joined + "\n"
    return joined


def migrate(issues, dry_run=False, rate_limit_delay=0.25):
    """Create Todoist inbox tasks from a list of Jira issues."""
    if not dry_run and not TODOIST_API_TOKEN:
        print("Error: TODOIST_API_TOKEN is not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)

    if not issues:
        print("No issues to migrate.")
        return 0, 0

    created = 0
    skipped = 0

    for issue in issues:
        fields = issue_to_task_fields(issue)
        try:
            create_task(
                content=fields["content"],
                description=fields["description"],
                dry_run=dry_run,
            )
            created += 1
            if not dry_run:
                time.sleep(rate_limit_delay)
        except requests.HTTPError as e:
            print(f"  ERROR creating task {issue['fields'].get('summary', '')!r}: {e}", file=sys.stderr)
            skipped += 1

    return created, skipped


def write_markdown(issues, epic_key, output_path):
    """Write Jira issues to a Markdown file as a task checklist."""
    lines = [f"# {epic_key}\n"]
    for issue in issues:
        fields = issue_to_task_fields(issue)
        lines.append(f"- [ ] {fields['content']}")
        if fields["description"]:
            for desc_line in fields["description"].splitlines():
                lines.append(f"  {desc_line}" if desc_line.strip() else "")
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {len(issues)} issue(s) to {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _check_jira_config():
    missing = [v for v in ("JIRA_BASE_URL", "JIRA_USERNAME", "JIRA_API_TOKEN") if not os.getenv(v)]
    if missing:
        print(f"Error: missing Jira config: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate a Jira Cloud epic to Todoist inbox"
    )
    parser.add_argument("--epic", help="Epic key to migrate (e.g. PROJ-123)")
    parser.add_argument("--list-epics", action="store_true", help="List epics in a project and exit")
    parser.add_argument("--list-projects", action="store_true", help="List all accessible projects and exit")
    parser.add_argument("--project", help="Jira project key (required for --list-epics)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without making any Todoist API calls",
    )
    parser.add_argument(
        "--output-md",
        metavar="FILE",
        help="Write issues to a Markdown file instead of creating Todoist tasks",
    )
    args = parser.parse_args()

    _check_jira_config()

    if args.list_projects:
        print("Fetching projects...")
        projects = list_projects()
        if not projects:
            print("No projects found.")
        for p in projects:
            print(f"  {p['key']:<12}  {p['name']}")
        return

    if args.list_epics:
        if not args.project:
            parser.error("--list-epics requires --project")
        print(f"Fetching epics for project {args.project!r}...")
        epics = list_epics(args.project)
        if not epics:
            print("No epics found.")
        for e in epics:
            status = e["fields"].get("status", {}).get("name", "")
            print(f"  {e['key']:<12}  [{status}]  {e['fields']['summary']}")
        return

    if not args.epic:
        parser.error("Provide --epic EPIC-KEY (or use --list-epics --project PROJ to find one)")

    print(f"Fetching issues from epic {args.epic!r}...")
    issues = get_epic_issues(args.epic)
    print(f"Found {len(issues)} issue(s).")

    if not issues:
        return

    if args.output_md:
        write_markdown(issues, args.epic, args.output_md)
        return

    print(f"\nMigrating to Todoist inbox{' [DRY RUN]' if args.dry_run else ''}...")
    created, skipped = migrate(issues, dry_run=args.dry_run)

    print(f"\nDone. Created: {created}, Skipped (errors): {skipped}")


if __name__ == "__main__":
    main()
