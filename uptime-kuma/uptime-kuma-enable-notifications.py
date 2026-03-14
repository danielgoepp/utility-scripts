"""
Enable notifications on all Uptime Kuma monitors.

This script retrieves all monitors and notifications from Uptime Kuma,
identifies monitors that are missing notification assignments, and enables
all available notifications on those monitors.
"""

import argparse

from uptime_kuma_api import UptimeKumaApi
from config import UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD


def connect_api():
    """Connect and authenticate to Uptime Kuma API."""
    api = UptimeKumaApi(UPTIME_KUMA_URL)
    api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)
    return api


def get_all_notification_ids(api):
    """Retrieve all notification IDs and display them."""
    notifications = api.get_notifications()
    print(f"Found {len(notifications)} notification(s):")
    for n in notifications:
        print(f"  - [{n['id']}] {n['name']} (type: {n.get('type', 'unknown')})")
    print()
    return [n["id"] for n in notifications]


def enable_notifications(api, notification_ids, dry_run=False):
    """
    Enable all notifications on monitors that are missing them.

    Args:
        api: UptimeKumaApi instance
        notification_ids: List of all notification IDs to assign
        dry_run: If True, only report what would be changed
    """
    monitors = api.get_monitors()
    notification_id_set = set(notification_ids)

    updated = 0
    skipped = 0

    for monitor in monitors:
        raw_type = monitor.get("type")
        monitor_type = raw_type.value if hasattr(raw_type, "value") else raw_type
        if monitor_type == "group":
            continue

        current_ids = set(monitor.get("notificationIDList") or [])
        name = monitor["name"]
        monitor_id = monitor["id"]

        if notification_id_set.issubset(current_ids):
            skipped += 1
            continue

        missing = notification_id_set - current_ids
        if dry_run:
            print(f"  [DRY RUN] {name} - would add notification IDs: {sorted(missing)}")
        else:
            api.edit_monitor(monitor_id, notificationIDList=sorted(notification_id_set))
            print(f"  Updated: {name} (added notification IDs: {sorted(missing)})")
        updated += 1

    print()
    print(f"{'Would update' if dry_run else 'Updated'}: {updated} monitor(s)")
    print(f"Already configured: {skipped} monitor(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Enable notifications on all Uptime Kuma monitors"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making updates",
    )
    args = parser.parse_args()

    api = connect_api()
    try:
        notification_ids = get_all_notification_ids(api)
        if not notification_ids:
            print("No notifications configured in Uptime Kuma. Nothing to do.")
            return

        if args.dry_run:
            print("Running in dry-run mode (no changes will be made)\n")

        print("Checking monitors for missing notifications...")
        enable_notifications(api, notification_ids, dry_run=args.dry_run)
    finally:
        api.disconnect()


if __name__ == "__main__":
    main()
