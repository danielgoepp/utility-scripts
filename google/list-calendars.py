"""
List all calendars in the authenticated Google account.

Usage:
    source .venv/bin/activate
    python3 google/list-calendars.py
"""

import argparse
from googleapiclient.discovery import build
from auth import get_credentials


def list_calendars(show_hidden: bool = False) -> list[dict]:
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    calendars = []
    page_token = None

    while True:
        response = (
            service.calendarList()
            .list(
                showHidden=show_hidden,
                pageToken=page_token,
            )
            .execute()
        )
        calendars.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return calendars


def main():
    parser = argparse.ArgumentParser(description="List all Google calendars")
    parser.add_argument(
        "--show-hidden",
        action="store_true",
        help="Include hidden calendars in the output",
    )
    args = parser.parse_args()

    calendars = list_calendars(show_hidden=args.show_hidden)

    if not calendars:
        print("No calendars found.")
        return

    print(f"Found {len(calendars)} calendar(s):\n")
    for cal in calendars:
        access_role = cal.get("accessRole", "unknown")
        primary = " [PRIMARY]" if cal.get("primary") else ""
        print(f"  {cal['summary']}{primary}")
        print(f"    ID:          {cal['id']}")
        print(f"    Access role: {access_role}")
        print(f"    Time zone:   {cal.get('timeZone', 'N/A')}")
        print()


if __name__ == "__main__":
    main()
