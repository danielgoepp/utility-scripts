"""
Import monitors from Excel spreadsheet into Uptime Kuma.

This script reads monitor definitions from an Excel file and creates
corresponding monitors in Uptime Kuma using the uptime-kuma-api library.
"""

import argparse
import json
import sys

import pandas as pd

# Excel file configuration
EXCEL_FILE = "/Users/dang/Documents/Household/General/Information Technology.xlsx"
SHEET_NAME = "Synthetic Tests"


def connect_api():
    """Connect and authenticate to Uptime Kuma API."""
    from uptime_kuma_api import UptimeKumaApi
    from config import UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD

    api = UptimeKumaApi(UPTIME_KUMA_URL)
    api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)
    return api


def get_existing_monitors(api):
    """Get list of existing monitors from Uptime Kuma."""
    monitors = api.get_monitors()
    return {monitor["name"]: monitor for monitor in monitors}


def load_monitors_from_excel():
    """Load monitor definitions from Excel spreadsheet."""
    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, header=0)
    return df


def map_monitor_type(excel_type):
    """Map Excel type column to Uptime Kuma MonitorType."""
    from uptime_kuma_api import MonitorType

    type_mapping = {
        "http": MonitorType.HTTP,
        "ping": MonitorType.PING,
        "port": MonitorType.PORT,
        "dns": MonitorType.DNS,
        "keyword": MonitorType.KEYWORD,
    }
    return type_mapping.get(excel_type.lower() if excel_type else None)


def build_monitor_config(row):
    """
    Build Uptime Kuma monitor configuration from Excel row.

    Args:
        row: pandas DataFrame row containing monitor definition

    Returns:
        dict: Monitor configuration for add_monitor() or None if invalid
    """
    from uptime_kuma_api import MonitorType

    excel_type = row.get("type")
    monitor_type = map_monitor_type(excel_type)

    if monitor_type is None:
        return None

    # Base configuration common to all monitor types
    config = {
        "type": monitor_type,
        "name": row.get("name"),
        "interval": 60,
    }

    # Type-specific configuration
    if monitor_type == MonitorType.HTTP:
        protocol = row.get("protocol", "https")
        host = row.get("host")
        port = row.get("port")

        # Build URL from components
        if port and port not in [80, 443]:
            url = f"{protocol}://{host}:{int(port)}"
        else:
            url = f"{protocol}://{host}"

        config.update({
            "url": url,
            "maxretries": 3,
            "accepted_statuscodes": ["200-299"],
            "ignoreTls": protocol == "http",
        })

    elif monitor_type == MonitorType.PING:
        config.update({
            "hostname": row.get("host"),
        })

    elif monitor_type == MonitorType.PORT:
        config.update({
            "hostname": row.get("host"),
            "port": int(row.get("port")) if row.get("port") else None,
        })

    return config


def create_monitor(api, config, dry_run=True):
    """
    Create a monitor in Uptime Kuma.

    Args:
        api: UptimeKumaApi instance
        config: Monitor configuration dict
        dry_run: If True, only print what would be created

    Returns:
        dict: API response or None if dry_run
    """
    if dry_run:
        print(f"[DRY RUN] Would create monitor: {config['name']}")
        print(json.dumps(config, indent=2, default=str))
        return None

    try:
        response = api.add_monitor(**config)
        print(f"Created monitor: {config['name']} (ID: {response.get('monitorID')})")
        return response
    except Exception as e:
        print(f"Error creating monitor '{config['name']}': {e}")
        return None


def import_monitors(api, dry_run=True, filter_type=None):
    """
    Import monitors from Excel into Uptime Kuma.

    Args:
        api: UptimeKumaApi instance
        dry_run: If True, only show what would be created
        filter_type: Optional type filter (e.g., 'http', 'ping')
    """
    # Get existing monitors to avoid duplicates
    existing = get_existing_monitors(api)
    print(f"Found {len(existing)} existing monitors in Uptime Kuma")

    # Load from Excel
    df = load_monitors_from_excel()
    print(f"Loaded {len(df)} entries from Excel")

    created = 0
    skipped = 0
    errors = 0

    for _, row in df.iterrows():
        # Apply type filter if specified
        if filter_type and row.get("type") != filter_type:
            continue

        name = row.get("name")

        # Skip if already exists
        if name in existing:
            print(f"Skipping '{name}' - already exists")
            skipped += 1
            continue

        # Build configuration
        config = build_monitor_config(row)
        if config is None:
            print(f"Skipping '{name}' - unsupported type: {row.get('type')}")
            skipped += 1
            continue

        # Create monitor
        result = create_monitor(api, config, dry_run=dry_run)
        if result is not None or dry_run:
            created += 1
        else:
            errors += 1

    print(f"\nSummary: {created} created, {skipped} skipped, {errors} errors")


def main():
    parser = argparse.ArgumentParser(
        description="Import monitors from Excel into Uptime Kuma"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be created without making changes (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create the monitors (disables dry-run)",
    )
    parser.add_argument(
        "--type",
        choices=["http", "ping", "port", "dns"],
        help="Only import monitors of this type",
    )
    parser.add_argument(
        "--list-excel",
        action="store_true",
        help="List monitors from Excel file and exit",
    )
    parser.add_argument(
        "--list-existing",
        action="store_true",
        help="List existing monitors in Uptime Kuma and exit",
    )

    args = parser.parse_args()

    # List Excel contents only
    if args.list_excel:
        df = load_monitors_from_excel()
        filtered = [
            row for _, row in df.iterrows()
            if not args.type or row.get("type") == args.type
        ]
        print(f"Monitors in Excel ({len(filtered)} shown, {len(df)} total):")
        print("-" * 60)
        for row in filtered:
            print(f"  [{row.get('type')}] {row.get('name')} - {row.get('host')}")
        return

    # Connect to API
    api = connect_api()

    try:
        # List existing monitors only
        if args.list_existing:
            monitors = api.get_monitors()
            print(f"Existing monitors in Uptime Kuma ({len(monitors)} total):")
            print("-" * 60)
            for monitor in monitors:
                print(f"  [{monitor['type']}] {monitor['name']}")
            return

        # Import monitors
        dry_run = not args.execute
        if dry_run:
            print("=" * 60)
            print("DRY RUN MODE - No changes will be made")
            print("Use --execute to actually create monitors")
            print("=" * 60)

        import_monitors(api, dry_run=dry_run, filter_type=args.type)

    finally:
        api.disconnect()


if __name__ == "__main__":
    main()
