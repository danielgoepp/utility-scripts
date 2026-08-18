"""
Disable notifications on all Uptime Kuma group monitors.

This script retrieves all monitors from Uptime Kuma and clears the
notification assignments on every group-type monitor, leaving individual
device monitors untouched.
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


def disable_group_notifications(api, monitors, dry_run=False):
    """Clear notificationIDList on every group-type monitor."""
    groups = [m for m in monitors if monitor_type(m) == "group"]

    updated = 0
    skipped = 0

    for monitor in groups:
        name = monitor["name"]
        current_ids = monitor.get("notificationIDList") or []

        if not current_ids:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {name} - would remove notification IDs: {sorted(current_ids)}")
        else:
            api.edit_monitor(monitor["id"], notificationIDList=[])
            print(f"  Updated: {name} (removed notification IDs: {sorted(current_ids)})")
        updated += 1

    print()
    print(f"{'Would update' if dry_run else 'Updated'}: {updated} group(s)")
    print(f"Already disabled: {skipped} group(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Disable notifications on all Uptime Kuma group monitors"
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

        if args.dry_run:
            print("Running in dry-run mode (no changes will be made)\n")

        print("Checking group monitors for notifications...")
        disable_group_notifications(api, monitors, dry_run=args.dry_run)
    finally:
        api.disconnect()


if __name__ == "__main__":
    main()
