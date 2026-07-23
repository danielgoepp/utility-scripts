#!/usr/bin/env python3

import argparse
import csv
import json
import requests
import sys
import config

DEVICE_CSV_FIELDS = [
    "hostName",
    "mac",
    "name",
    "model",
    "shortname",
    "ip",
    "productLine",
    "status",
    "version",
    "firmwareStatus",
    "updateAvailable",
    "isConsole",
    "isManaged",
    "startupTime",
    "adoptionTime",
    "note",
]


def get_unifi_data():
    """Fetch UniFi hosts and devices data from cloud API."""
    if not config.UNIFI_CLOUD_API_KEY:
        raise ValueError("UNIFI_API_KEY environment variable is required")

    headers = {
        "X-API-KEY": config.UNIFI_CLOUD_API_KEY,
        "Accept": "application/json",
    }

    try:
        # Get all the hosts (ui-protect and ui-network)
        hosts_response = requests.get("https://api.ui.com/v1/hosts", headers=headers)
        hosts_response.raise_for_status()

        # Get all the unifi devices (but not devices on the network)
        devices_response = requests.get("https://api.ui.com/v1/devices", headers=headers)
        devices_response.raise_for_status()

        return {
            "hosts": hosts_response.json(),
            "devices": devices_response.json()
        }

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            print(
                f"Error fetching UniFi data: {e} — the cloud API key "
                "(UNIFI_API_KEY) is missing, invalid, or unauthorized",
                file=sys.stderr,
            )
        else:
            print(f"Error fetching UniFi data: {e}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching UniFi data: {e}", file=sys.stderr)
        return None


def print_devices_csv(data):
    """Print devices (excluding the uidb icon/image metadata) as CSV."""
    writer = csv.DictWriter(sys.stdout, fieldnames=DEVICE_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()

    for host_entry in data["devices"].get("data", []):
        row_context = {
            "hostId": host_entry.get("hostId"),
            "hostName": host_entry.get("hostName"),
        }
        for device in host_entry.get("devices", []):
            row = {**row_context, **device}
            writer.writerow(row)


def main():
    """Main function to fetch and display UniFi device data."""
    parser = argparse.ArgumentParser(description="Fetch UniFi hosts and devices from the cloud API")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="csv",
        help="Output format (default: csv, devices only, excluding uidb data). "
             "json outputs the full raw hosts+devices response.",
    )
    args = parser.parse_args()

    try:
        data = get_unifi_data()
        if not data:
            sys.exit(1)

        if args.format == "csv":
            print_devices_csv(data)
        else:
            print(json.dumps(data, indent=4))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
