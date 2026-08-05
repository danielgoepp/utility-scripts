"""
Set the retry count on all monitors within a parent group.

Finds a group monitor by name, then updates every monitor whose parent is
that group to use the given number of retries before a down notification
is sent (Uptime Kuma's "Retries" / maxretries field).
"""

import argparse

from uptime_kuma_api import UptimeKumaApi
from config import UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD


def connect_api():
    """Connect and authenticate to Uptime Kuma API."""
    api = UptimeKumaApi(UPTIME_KUMA_URL)
    api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)
    return api


def monitor_type(monitor):
    raw_type = monitor.get("type")
    return raw_type.value if hasattr(raw_type, "value") else raw_type


def find_group(monitors, group_name):
    """Find a group monitor by exact (case-insensitive) name match."""
    matches = [
        m
        for m in monitors
        if monitor_type(m) == "group" and m["name"].lower() == group_name.lower()
    ]
    if len(matches) > 1:
        raise SystemExit(f"Multiple groups found matching '{group_name}'")
    return matches[0] if matches else None


def set_group_retries(api, monitors, group, retries, dry_run=False):
    """Set maxretries on every monitor whose parent is the given group."""
    children = [m for m in monitors if m.get("parent") == group["id"]]

    if not children:
        print(f"No monitors found under group '{group['name']}'")
        return

    updated = 0
    skipped = 0

    for monitor in children:
        name = monitor["name"]
        current_retries = monitor.get("maxretries", 0)

        if current_retries == retries:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {name} - would set retries: {current_retries} -> {retries}")
        else:
            api.edit_monitor(monitor["id"], maxretries=retries)
            print(f"  Updated: {name} (retries: {current_retries} -> {retries})")
        updated += 1

    print()
    print(f"{'Would update' if dry_run else 'Updated'}: {updated} monitor(s)")
    print(f"Already set: {skipped} monitor(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Set the retry count on all monitors within a parent group"
    )
    parser.add_argument("--group", required=True, help="Name of the parent group")
    parser.add_argument(
        "--retries",
        type=int,
        required=True,
        help="Number of retries before a down notification is sent",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making updates",
    )
    args = parser.parse_args()

    api = connect_api()
    try:
        monitors = api.get_monitors()
        group = find_group(monitors, args.group)
        if not group:
            raise SystemExit(f"No group found matching '{args.group}'")

        print(f"Found group '{group['name']}' (id {group['id']})")
        if args.dry_run:
            print("Running in dry-run mode (no changes will be made)\n")

        set_group_retries(api, monitors, group, args.retries, dry_run=args.dry_run)
    finally:
        api.disconnect()


if __name__ == "__main__":
    main()
