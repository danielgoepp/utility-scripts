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
    "status",
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


def get_host_reservations():
    """Fetch configured dnsmasq host reservations (static IP/MAC mappings)."""
    if not config.OPNSENSE_URL or not config.OPNSENSE_API_KEY or not config.OPNSENSE_API_SECRET:
        raise ValueError(
            "OPNSENSE_URL, OPNSENSE_API_KEY, and OPNSENSE_API_SECRET environment variables are required"
        )

    url = f"{config.OPNSENSE_URL.rstrip('/')}/api/dnsmasq/settings/search_host"

    try:
        response = requests.post(
            url,
            auth=(config.OPNSENSE_API_KEY, config.OPNSENSE_API_SECRET),
            verify=config.OPNSENSE_VERIFY_SSL,
        )
        response.raise_for_status()
        return response.json().get("rows", [])
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            print(
                f"Error fetching dnsmasq host reservations: {e} — the API key/secret is "
                "missing, invalid, or unauthorized",
                file=sys.stderr,
            )
        else:
            print(f"Error fetching dnsmasq host reservations: {e}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dnsmasq host reservations: {e}", file=sys.stderr)
        return None


def add_inactive_reservations(rows):
    """Append reservations that have no corresponding active lease, marked as such."""
    reservations = get_host_reservations()
    if reservations is None:
        return None

    leased_ips = {lease.get("address") for lease in rows if lease.get("address")}
    for reservation in reservations:
        ip = reservation.get("ip")
        if not ip or ip in leased_ips:
            continue
        rows.append(
            {
                "address": ip,
                "status": "reserved (no active lease)",
                "hostname": reservation.get("host", ""),
                "hwaddr": reservation.get("hwaddr", ""),
                "mac_info": "",
                "if_descr": "",
                "expire": None,
                "is_reserved": [],
                "client_id": reservation.get("client_id", ""),
            }
        )
    return rows


def print_leases_csv(rows):
    """Print leases as CSV."""
    writer = csv.DictWriter(sys.stdout, fieldnames=LEASE_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for lease in rows:
        row = dict(lease)
        row["status"] = lease.get("status") or "active"
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
    parser.add_argument(
        "--no-reservations", action="store_true",
        help="Omit configured host reservations that have no active lease (by default, "
        "they're included with status 'reserved (no active lease)').",
    )
    args = parser.parse_args()

    try:
        data = get_leases()
        if not data:
            sys.exit(1)

        rows = data.get("rows", [])

        if not args.no_reservations:
            rows = add_inactive_reservations(rows)
            if rows is None:
                sys.exit(1)

        if args.format == "csv":
            print_leases_csv(rows)
        else:
            print(json.dumps(rows, indent=4))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
