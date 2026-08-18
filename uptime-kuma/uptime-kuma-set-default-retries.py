"""
Set the retry count on all Uptime Kuma monitors.

Updates every monitor (including group monitors) to use the given number of
retries before a down notification is sent (Uptime Kuma's "Retries" /
maxretries field).
"""

import argparse

from uptime_kuma_api import UptimeKumaApi
from uptime_kuma_api.api import _convert_monitor_input, _check_arguments_monitor
from uptime_kuma_api.event import Event
from config import UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD


def connect_api():
    """Connect and authenticate to Uptime Kuma API."""
    api = UptimeKumaApi(UPTIME_KUMA_URL)
    api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)
    return api


def safe_edit_monitor(api, id_, **kwargs):
    """
    Like api.edit_monitor(), but tolerates monitor types the installed
    uptime-kuma-api version doesn't recognize for argument validation
    (e.g. "smtp"), by skipping just that validation step for them.
    """
    data = api.get_monitor(id_)
    data.update(kwargs)
    _convert_monitor_input(data)
    try:
        _check_arguments_monitor(data)
    except KeyError:
        pass
    with api.wait_for_event(Event.MONITOR_LIST):
        return api._call('editMonitor', data)


def set_default_retries(api, monitors, retries, dry_run=False):
    """Set maxretries on every monitor."""
    updated = 0
    skipped = 0

    for monitor in monitors:
        name = monitor["name"]
        current_retries = monitor.get("maxretries", 0)

        if current_retries == retries:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {name} - would set retries: {current_retries} -> {retries}")
        else:
            safe_edit_monitor(api, monitor["id"], maxretries=retries)
            print(f"  Updated: {name} (retries: {current_retries} -> {retries})")
        updated += 1

    print()
    print(f"{'Would update' if dry_run else 'Updated'}: {updated} monitor(s)")
    print(f"Already set: {skipped} monitor(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Set the retry count on all Uptime Kuma monitors"
    )
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

        if args.dry_run:
            print("Running in dry-run mode (no changes will be made)\n")

        set_default_retries(api, monitors, args.retries, dry_run=args.dry_run)
    finally:
        api.disconnect()


if __name__ == "__main__":
    main()
