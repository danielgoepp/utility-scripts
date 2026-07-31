#!/usr/bin/env python3

import argparse
import csv
import json
import sys
from datetime import datetime, timezone

import requests
import config

LEASE_CSV_FIELDS = [
    "address",
    "hostname",
    "hwaddr",
    "mac_info",
    "if_descr",
    "expires",
    "is_reserved",
    "client_id",
]


def get_leases():
    """Fetch active leases from the OPNsense dnsmasq API."""
    if not config.OPNSENSE_URL or not config.OPNSENSE_API_KEY or not config.OPNSENSE_API_SECRET:
        raise ValueError(
            "OPNSENSE_URL, OPNSENSE_API_KEY, and OPNSENSE_API_SECRET environment variables are required"
        )

    url = f"{config.OPNSENSE_URL.rstrip('/')}/api/dnsmasq/leases/search"

    try:
        response = requests.get(
            url,
            auth=(config.OPNSENSE_API_KEY, config.OPNSENSE_API_SECRET),
            verify=config.OPNSENSE_VERIFY_SSL,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            print(
                f"Error fetching dnsmasq leases: {e} — the API key/secret is missing, "
                "invalid, or unauthorized",
                file=sys.stderr,
            )
        else:
            print(f"Error fetching dnsmasq leases: {e}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dnsmasq leases: {e}", file=sys.stderr)
        return None


def print_leases_csv(rows):
    """Print leases as CSV."""
    writer = csv.DictWriter(sys.stdout, fieldnames=LEASE_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for lease in rows:
        row = dict(lease)
        row["is_reserved"] = ",".join(lease.get("is_reserved") or [])
        expire = lease.get("expire")
        row["expires"] = (
            datetime.fromtimestamp(int(expire), tz=timezone.utc).isoformat() if expire else ""
        )
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Fetch active DHCP leases from OPNsense dnsmasq")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="csv",
        help="Output format (default: csv). json outputs the full raw API response.",
    )
    args = parser.parse_args()

    try:
        data = get_leases()
        if not data:
            sys.exit(1)

        rows = data.get("rows", [])

        if args.format == "csv":
            print_leases_csv(rows)
        else:
            print(json.dumps(rows, indent=4))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
