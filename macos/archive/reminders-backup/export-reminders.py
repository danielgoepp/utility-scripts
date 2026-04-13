#!/usr/bin/env python3
"""Export all macOS Reminders to JSON or CSV.

Requires macOS with pyobjc-framework-EventKit installed. On first run,
the system will prompt for permission to access Reminders.
"""

import argparse
import csv
import json
import sys
import threading
from datetime import datetime, timezone

import EventKit


def nsdate_to_iso(nsdate):
    """Convert an NSDate to an ISO 8601 string."""
    if nsdate is None:
        return None
    ts = nsdate.timeIntervalSince1970()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


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
                "priority": int(r.priority()),
                "flagged": bool(r.flagged()) if hasattr(r, "flagged") else False,
                "creationDate": nsdate_to_iso(r.creationDate()),
                "modificationDate": nsdate_to_iso(r.lastModifiedDate()),
            }
        )

    return results


def priority_label(value):
    """Convert numeric priority to human-readable label."""
    if value == 0:
        return "none"
    elif 1 <= value <= 4:
        return "high"
    elif value == 5:
        return "medium"
    elif 6 <= value <= 9:
        return "low"
    return "none"


def write_json(reminders, output_file):
    """Write reminders to a JSON file."""
    with open(output_file, "w") as f:
        json.dump(reminders, f, indent=2)
    print(f"Exported {len(reminders)} reminders to {output_file}")


def write_csv(reminders, output_file):
    """Write reminders to a CSV file."""
    if not reminders:
        print("No reminders to export.")
        return

    fieldnames = [
        "list",
        "name",
        "body",
        "completed",
        "completionDate",
        "dueDate",
        "priority",
        "flagged",
        "creationDate",
        "modificationDate",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reminders)

    print(f"Exported {len(reminders)} reminders to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Export all macOS Reminders to JSON or CSV"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: reminders-YYYY-MM-DD.{format})",
    )
    parser.add_argument(
        "--incomplete-only",
        action="store_true",
        help="Export only incomplete reminders",
    )
    parser.add_argument(
        "--list",
        dest="filter_list",
        help="Export only reminders from this list",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing to a file",
    )
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    reminders = fetch_reminders()

    if args.incomplete_only:
        reminders = [r for r in reminders if not r["completed"]]

    if args.filter_list:
        reminders = [
            r for r in reminders if r["list"].lower() == args.filter_list.lower()
        ]

    # Add human-readable priority
    for r in reminders:
        r["priority"] = priority_label(r["priority"])

    if args.stdout:
        if args.format == "json":
            print(json.dumps(reminders, indent=2))
        else:
            if reminders:
                fieldnames = list(reminders[0].keys())
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(reminders)
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = args.output or f"reminders-{date_str}.{args.format}"

    if args.format == "json":
        write_json(reminders, output_file)
    else:
        write_csv(reminders, output_file)


if __name__ == "__main__":
    main()
