"""
Delete or unsubscribe from a Google Calendar.

For owned calendars, you are prompted to choose between:
  - Permanently deleting the calendar and all its events
  - Just removing it from your calendar list (hiding it without deleting)

Non-owned calendars (reader, writer) are always just removed from your list.
The primary calendar cannot be deleted or removed.

Usage:
    source .venv/bin/activate

    # Interactive: lists calendars and prompts you to pick one
    python3 google/delete-calendar.py

    # Direct: specify a calendar ID
    python3 google/delete-calendar.py --id <calendarId>

    # Skip the owned/unsubscribe choice — force remove-from-list only
    python3 google/delete-calendar.py --id <calendarId> --remove-from-list
"""

import argparse
import sys
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auth import get_credentials


def fetch_calendars(service) -> list[dict]:
    calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(pageToken=page_token).execute()
        calendars.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return calendars


def pick_calendar(calendars: list[dict]) -> dict:
    print("Available calendars:\n")
    for i, cal in enumerate(calendars):
        primary = " [PRIMARY]" if cal.get("primary") else ""
        role = cal.get("accessRole", "unknown")
        print(f"  [{i + 1}] {cal['summary']}{primary}  ({role})")
    print()

    while True:
        raw = input("Enter the number of the calendar to select: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(calendars):
            return calendars[int(raw) - 1]
        print(f"Please enter a number between 1 and {len(calendars)}.")


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer == "y"


def choose_action_for_owned_calendar(name: str) -> str:
    """For owned calendars, ask whether to permanently delete or just remove from list."""
    print(f"\nYou own '{name}'. Choose an action:\n")
    print("  [1] Permanently delete — removes the calendar and ALL its events forever")
    print("  [2] Remove from my list — hides it from your account without deleting it")
    print()

    while True:
        raw = input("Enter 1 or 2: ").strip()
        if raw == "1":
            return "delete"
        if raw == "2":
            return "remove"
        print("Please enter 1 or 2.")


def delete_calendar(service, cal: dict, force_remove_from_list: bool = False) -> None:
    cal_id = cal["id"]
    name = cal["summary"]
    role = cal.get("accessRole", "unknown")
    is_primary = cal.get("primary", False)

    if is_primary:
        print(f"Error: '{name}' is your primary calendar and cannot be removed.")
        sys.exit(1)

    if role == "owner" and not force_remove_from_list:
        action = choose_action_for_owned_calendar(name)
    else:
        action = "remove"

    if action == "delete":
        warning = "This will permanently delete the calendar and ALL its events. This cannot be undone."
    else:
        warning = "This will remove the calendar from your list. The calendar itself will not be affected."

    print(f"\nCalendar: {name}")
    print(f"ID:       {cal_id}")
    print(f"Note:     {warning}\n")

    if not confirm("Are you sure you want to proceed?"):
        print("Aborted.")
        sys.exit(0)

    try:
        if action == "delete":
            service.calendars().delete(calendarId=cal_id).execute()
            print(f"Deleted calendar '{name}'.")
        else:
            service.calendarList().delete(calendarId=cal_id).execute()
            print(f"Removed '{name}' from your calendar list.")
    except HttpError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Delete or unsubscribe from a Google Calendar")
    parser.add_argument("--id", metavar="CALENDAR_ID", help="Calendar ID (skips interactive selection)")
    parser.add_argument(
        "--remove-from-list",
        action="store_true",
        help="For owned calendars: remove from your list instead of permanently deleting",
    )
    args = parser.parse_args()

    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    calendars = fetch_calendars(service)

    if args.id:
        matches = [c for c in calendars if c["id"] == args.id]
        if not matches:
            print(f"Error: No calendar found with ID '{args.id}'.")
            sys.exit(1)
        cal = matches[0]
    else:
        cal = pick_calendar(calendars)

    delete_calendar(service, cal, force_remove_from_list=args.remove_from_list)


if __name__ == "__main__":
    main()
