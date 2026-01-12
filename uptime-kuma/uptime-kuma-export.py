"""
Export monitors from Uptime Kuma to an Excel spreadsheet.

This script retrieves all monitor definitions from Uptime Kuma and exports
them to an Excel file for backup or documentation purposes.
"""

import re

import pandas as pd


OUTPUT_FILE = "/Users/dang/backups/uptime-kuma/Uptime Kuma Monitors.xlsx"


def connect_api():
    """Connect and authenticate to Uptime Kuma API."""
    from uptime_kuma_api import UptimeKumaApi
    from config import UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD

    api = UptimeKumaApi(UPTIME_KUMA_URL)
    api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)
    return api


def build_monitor_group_map(monitors):
    """Build a mapping of monitor ID to monitor name for group lookups."""
    return {monitor["id"]: monitor["name"] for monitor in monitors}


def extract_monitor_data(monitor, group_map):
    """
    Extract relevant fields from a monitor for export.

    Args:
        monitor: Monitor dict from Uptime Kuma API
        group_map: Dict mapping monitor IDs to names

    Returns:
        dict: Extracted monitor data for export
    """
    raw_type = monitor.get("type")
    monitor_type = raw_type.value if hasattr(raw_type, "value") else raw_type

    # Determine target based on monitor type
    if monitor_type == "http":
        target = monitor.get("url") or ""
    elif monitor_type == "postgres":
        # Mask password in connection string
        conn_str = monitor.get("databaseConnectionString") or ""
        target = re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", conn_str)
    else:
        target = monitor.get("hostname") or ""

    return {
        "Name": monitor.get("name", ""),
        "Type": monitor_type,
        "Target": target,
        "Port": monitor.get("port"),
        "Interval (seconds)": monitor.get("interval"),
        "Certificate Expiry Check": monitor.get("expiryNotification", False),
        "Upside Down": monitor.get("upsideDown", False),
        "Group": group_map.get(monitor.get("parent"), ""),
        "Resolver Server": monitor.get("dns_resolve_server") if monitor_type == "dns" else "",
        "Record Type": monitor.get("dns_resolve_type") if monitor_type == "dns" else "",
    }


def export_monitors(api, output_file):
    """
    Export all monitors from Uptime Kuma to Excel.

    Args:
        api: UptimeKumaApi instance
        output_file: Path to output Excel file

    Returns:
        int: Number of monitors exported
    """
    # Get all monitors
    monitors = api.get_monitors()
    print(f"Retrieved {len(monitors)} monitors from Uptime Kuma")

    # Build group map for resolving parent references
    group_map = build_monitor_group_map(monitors)

    # Extract data for each monitor, excluding group-type monitors
    export_data = []
    for monitor in monitors:
        raw_type = monitor.get("type")
        if (raw_type.value if hasattr(raw_type, "value") else raw_type) == "group":
            continue
        data = extract_monitor_data(monitor, group_map)
        export_data.append(data)

    # Create DataFrame and sort by group then name
    df = pd.DataFrame(export_data)
    df = df.sort_values(by=["Group", "Name"], key=lambda x: x.str.lower())

    # Export to Excel
    df.to_excel(output_file, index=False, sheet_name="Monitors")
    print(f"Exported {len(monitors)} monitors to {output_file}")

    return len(monitors)


if __name__ == "__main__":
    api = connect_api()
    try:
        export_monitors(api, OUTPUT_FILE)
    finally:
        api.disconnect()
