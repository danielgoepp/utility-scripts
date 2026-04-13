#!/usr/bin/env python3
"""Migrate macOS Reminders to Todoist.

Reads all Reminders via EventKit and creates matching projects/tasks in Todoist.
Requires macOS with pyobjc-framework-EventKit installed. On first run, the
system will prompt for permission to access Reminders.

Setup:
    cp macos/.env.example macos/.env
    # Fill in TODOIST_API_TOKEN
    source .venv/bin/activate
    pip install requests pyobjc-framework-EventKit python-dotenv
    python3 macos/todoist/migrate-reminders-to-todoist.py --incomplete-only
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import EventKit

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
TODOIST_BASE_URL = "https://api.todoist.com/api/v1"

# Reminders priority → Todoist priority
# Todoist: 1=normal (p4), 2=low (p3), 3=medium (p2), 4=urgent (p1)
PRIORITY_MAP = {
    "none": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
}


# ---------------------------------------------------------------------------
# EventKit helpers
# ---------------------------------------------------------------------------

def nsdate_to_iso(nsdate):
    if nsdate is None:
        return None
    ts = nsdate.timeIntervalSince1970()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def priority_label(value):
    if value == 0:
        return "none"
    elif 1 <= value <= 4:
        return "high"
    elif value == 5:
        return "medium"
    elif 6 <= value <= 9:
        return "low"
    return "none"


def fetch_reminders():
    """Fetch all reminders from macOS Reminders via EventKit."""
    store = EventKit.EKEventStore.alloc().init()

    sem = threading.Semaphore(0)
    granted = [False]

    def auth_handler(g, err):
        granted[0] = g
        sem.release()

    store.requestFullAccessToRemindersWithCompletion_(auth_handler)
    sem.acquire()

    if not granted[0]:
        print("Error: access to Reminders was denied.", file=sys.stderr)
        print(
            "Grant access in System Settings > Privacy & Security > Reminders.",
            file=sys.stderr,
        )
        sys.exit(1)

    calendars = store.calendarsForEntityType_(EventKit.EKEntityTypeReminder)
    predicate = store.predicateForRemindersInCalendars_(calendars)

    sem2 = threading.Semaphore(0)
    all_reminders = [None]

    def fetch_handler(reminders):
        all_reminders[0] = reminders
        sem2.release()

    store.fetchRemindersMatchingPredicate_completion_(predicate, fetch_handler)
    sem2.acquire()

    results = []
    for r in all_reminders[0]:
        due = r.dueDateComponents()
        due_date = nsdate_to_iso(due.date()) if due and due.date() else None
        results.append(
            {
                "list": r.calendar().title(),
                "name": r.title(),
                "body": str(r.notes()) if r.notes() else "",
                "completed": bool(r.isCompleted()),
                "completionDate": nsdate_to_iso(r.completionDate()),
                "dueDate": due_date,
                "priority": priority_label(int(r.priority())),
                "flagged": bool(r.flagged()) if hasattr(r, "flagged") else False,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Todoist API helpers
# ---------------------------------------------------------------------------

def _headers():
    return {"Authorization": f"Bearer {TODOIST_API_TOKEN}"}


def get_projects():
    """Return a dict of {name: id} for all existing Todoist projects."""
    projects = {}
    cursor = None
    while True:
        params = {}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{TODOIST_BASE_URL}/projects", headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for p in data["results"]:
            projects[p["name"]] = p["id"]
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return projects


def create_project(name, dry_run=False):
    if dry_run:
        print(f"  [dry-run] Would create project: {name!r}")
        return f"dry-run-project-{name}"
    resp = requests.post(
        f"{TODOIST_BASE_URL}/projects",
        headers=_headers(),
        json={"name": name},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def create_task(reminder, project_id, dry_run=False):
    payload = {
        "content": reminder["name"],
        "project_id": project_id,
        "priority": PRIORITY_MAP.get(reminder["priority"], 1),
    }

    if reminder["body"]:
        payload["description"] = reminder["body"]

    if reminder["dueDate"]:
        # Todoist accepts due_datetime (ISO 8601 with time) or due_date (YYYY-MM-DD)
        iso = reminder["dueDate"]
        if "T" in iso:
            payload["due_datetime"] = iso
        else:
            payload["due_date"] = iso

    if reminder["flagged"]:
        payload["labels"] = ["flagged"]

    if dry_run:
        print(f"  [dry-run] Would create task: {reminder['name']!r} (priority={reminder['priority']}, due={reminder.get('dueDate')})")
        return f"dry-run-task-{reminder['name']}"

    resp = requests.post(
        f"{TODOIST_BASE_URL}/tasks",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def close_task(task_id, dry_run=False):
    if dry_run:
        print(f"  [dry-run] Would mark task {task_id!r} as complete")
        return
    resp = requests.post(
        f"{TODOIST_BASE_URL}/tasks/{task_id}/close",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Main migration logic
# ---------------------------------------------------------------------------

def migrate(reminders, dry_run=False, include_completed=False, rate_limit_delay=0.2):
    """Migrate reminders to Todoist. Returns (created, skipped) counts."""
    if not dry_run and not TODOIST_API_TOKEN:
        print("Error: TODOIST_API_TOKEN is not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)

    if not include_completed:
        reminders = [r for r in reminders if not r["completed"]]

    if not reminders:
        print("No reminders to migrate.")
        return 0, 0

    print(f"Fetching existing Todoist projects...")
    if dry_run:
        existing_projects = {}
    else:
        existing_projects = get_projects()

    project_id_cache = dict(existing_projects)
    created_count = 0
    skipped_count = 0

    # Group by list for cleaner output
    lists = sorted({r["list"] for r in reminders})
    for list_name in lists:
        list_reminders = [r for r in reminders if r["list"] == list_name]
        print(f"\nList: {list_name!r} ({len(list_reminders)} reminders)")

        # Get or create project
        if list_name not in project_id_cache:
            print(f"  Creating project {list_name!r}...")
            project_id = create_project(list_name, dry_run=dry_run)
            project_id_cache[list_name] = project_id
        else:
            print(f"  Using existing project {list_name!r} (id={project_id_cache[list_name]})")
            project_id = project_id_cache[list_name]

        for reminder in list_reminders:
            try:
                task_id = create_task(reminder, project_id, dry_run=dry_run)
                if reminder["completed"]:
                    close_task(task_id, dry_run=dry_run)
                created_count += 1
                if not dry_run:
                    time.sleep(rate_limit_delay)
            except requests.HTTPError as e:
                print(f"  ERROR creating {reminder['name']!r}: {e}", file=sys.stderr)
                skipped_count += 1

    return created_count, skipped_count


def main():
    parser = argparse.ArgumentParser(
        description="Migrate macOS Reminders to Todoist"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without making any API calls",
    )
    parser.add_argument(
        "--include-completed",
        action="store_true",
        help="Also migrate completed reminders (marked complete in Todoist)",
    )
    parser.add_argument(
        "--list",
        dest="filter_list",
        help="Only migrate reminders from this list (case-insensitive)",
    )
    parser.add_argument(
        "--dump-json",
        metavar="FILE",
        help="Dump fetched reminders to a JSON file before migrating (useful for inspection)",
    )
    args = parser.parse_args()

    print("Fetching reminders from macOS...")
    reminders = fetch_reminders()
    print(f"Found {len(reminders)} total reminders.")

    if args.filter_list:
        reminders = [r for r in reminders if r["list"].lower() == args.filter_list.lower()]
        print(f"Filtered to {len(reminders)} reminders in list {args.filter_list!r}.")

    if args.dump_json:
        with open(args.dump_json, "w") as f:
            json.dump(reminders, f, indent=2)
        print(f"Dumped reminders to {args.dump_json}")

    created, skipped = migrate(
        reminders,
        dry_run=args.dry_run,
        include_completed=args.include_completed,
    )

    print(f"\nDone. Created: {created}, Skipped (errors): {skipped}")


if __name__ == "__main__":
    main()
