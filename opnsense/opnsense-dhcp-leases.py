#!/usr/bin/env python3

import argparse
import csv
import json
import sys
import requests
import config

LEASE_CSV_FIELDS = [
    "address",
    "hostname",
    "mac",
    "if",
    "if_descr",
    "type",
    "state",
    "starts",
    "ends",
    "man",
    "descr",
]


def get_leases():
    """Fetch DHCPv4 leases from the OPNsense legacy ISC DHCP API."""
    if not config.OPNSENSE_URL or not config.OPNSENSE_API_KEY or not config.OPNSENSE_API_SECRET:
        raise ValueError(
            "OPNSENSE_URL, OPNSENSE_API_KEY, and OPNSENSE_API_SECRET environment variables are required"
        )

    url = f"{config.OPNSENSE_URL.rstrip('/')}/api/dhcpv4/leases/searchLease"

    try:
        response = requests.post(
            url,
            json={"current": 1, "rowCount": -1, "sort": {}, "searchPhrase": ""},
            auth=(config.OPNSENSE_API_KEY, config.OPNSENSE_API_SECRET),
            verify=config.OPNSENSE_VERIFY_SSL,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            print(
                f"Error fetching DHCP leases: {e} — the API key/secret is missing, "
                "invalid, or unauthorized",
                file=sys.stderr,
            )
        else:
            print(f"Error fetching DHCP leases: {e}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching DHCP leases: {e}", file=sys.stderr)
        return None


def print_leases_csv(data):
    """Print leases as CSV."""
    writer = csv.DictWriter(sys.stdout, fieldnames=LEASE_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for lease in data.get("rows", []):
        writer.writerow(lease)


def main():
    parser = argparse.ArgumentParser(description="Fetch DHCPv4 leases from OPNsense (legacy ISC DHCP)")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="csv",
        help="Output format (default: csv). json outputs the full raw API response.",
    )
    args = parser.parse_args()

    try:
        data = get_leases()
        if not data:
            sys.exit(1)

        if args.format == "csv":
            print_leases_csv(data)
        else:
            print(json.dumps(data, indent=4))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
