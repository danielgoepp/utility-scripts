#!/usr/bin/env python3

import argparse
import sys
import requests
import config

AUTH = None
SESSION = None


def api_get(path, params=None):
    url = f"{config.OPNSENSE_URL.rstrip('/')}{path}"
    response = SESSION.get(url, params=params, auth=AUTH, verify=config.OPNSENSE_VERIFY_SSL)
    response.raise_for_status()
    return response.json()


def api_post(path, payload=None):
    url = f"{config.OPNSENSE_URL.rstrip('/')}{path}"
    response = SESSION.post(url, json=payload or {}, auth=AUTH, verify=config.OPNSENSE_VERIFY_SSL)
    response.raise_for_status()
    return response.json()


def get_static_leases():
    """Fetch ISC DHCPv4 static reservations (legacy leases API, filtered to type=static)."""
    data = api_get("/api/dhcpv4/leases/search_lease")
    return [row for row in data.get("rows", []) if row.get("type") == "static"]


def get_existing_dnsmasq_hosts():
    """Fetch existing dnsmasq host reservations, for idempotent re-runs."""
    data = api_post("/api/dnsmasq/settings/search_host")
    return data.get("rows", [])


def build_host_payload(lease, domain):
    return {
        "host": lease.get("hostname", ""),
        "domain": domain,
        "ip": lease.get("address", ""),
        "hwaddr": lease.get("mac", ""),
        "descr": lease.get("descr", ""),
        "local": "1",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Import ISC DHCP static reservations into dnsmasq host reservations "
        "(part of the ISC DHCP -> dnsmasq migration)"
    )
    parser.add_argument(
        "--domain", default=config.OPNSENSE_INTERNAL_DOMAIN,
        help="Domain to stamp on every reservation (default: OPNSENSE_INTERNAL_DOMAIN from .env)",
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Actually create the reservations. Without this flag, only prints what would happen.",
    )
    parser.add_argument(
        "--reconfigure", action="store_true",
        help="After committing, reload dnsmasq to apply the new reservations (requires --commit).",
    )
    args = parser.parse_args()

    if not config.OPNSENSE_URL or not config.OPNSENSE_API_KEY or not config.OPNSENSE_API_SECRET:
        print(
            "OPNSENSE_URL, OPNSENSE_API_KEY, and OPNSENSE_API_SECRET environment variables are required",
            file=sys.stderr,
        )
        sys.exit(1)
    if not args.domain:
        print(
            "No domain specified. Pass --domain or set OPNSENSE_INTERNAL_DOMAIN in .env — "
            "OPNsense will not reliably resolve reservations via Unbound with a blank domain.",
            file=sys.stderr,
        )
        sys.exit(1)

    global AUTH, SESSION
    AUTH = (config.OPNSENSE_API_KEY, config.OPNSENSE_API_SECRET)
    SESSION = requests.Session()

    try:
        static_leases = get_static_leases()
        existing_hosts = get_existing_dnsmasq_hosts()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from OPNsense: {e}", file=sys.stderr)
        sys.exit(1)

    existing_ips = {h.get("ip", "").lower() for h in existing_hosts}
    existing_macs = {h.get("hwaddr", "").lower() for h in existing_hosts if h.get("hwaddr")}

    created, skipped, failed = 0, 0, 0

    for lease in static_leases:
        ip = lease.get("address", "")
        mac = lease.get("mac", "")
        hostname = lease.get("hostname", "") or "(no hostname)"

        if not ip or not mac:
            print(f"SKIP  {hostname:30} missing IP or MAC, cannot create reservation", file=sys.stderr)
            skipped += 1
            continue

        if ip.lower() in existing_ips or mac.lower() in existing_macs:
            print(f"SKIP  {hostname:30} {ip:16} {mac}  (already present in dnsmasq)")
            skipped += 1
            continue

        payload = build_host_payload(lease, args.domain)

        if not args.commit:
            print(f"WOULD ADD  {hostname:30} {ip:16} {mac}  domain={args.domain}")
            continue

        try:
            result = api_post("/api/dnsmasq/settings/add_host", {"host": payload})
            if result.get("result") == "saved":
                print(f"ADDED  {hostname:30} {ip:16} {mac}")
                created += 1
            else:
                print(f"FAILED {hostname:30} {ip:16} {mac}  {result}", file=sys.stderr)
                failed += 1
        except requests.exceptions.RequestException as e:
            print(f"FAILED {hostname:30} {ip:16} {mac}  {e}", file=sys.stderr)
            failed += 1

    print(
        f"\n{len(static_leases)} static reservation(s) found. "
        f"{'Created' if args.commit else 'Would create'}: {created if args.commit else len(static_leases) - skipped}, "
        f"skipped: {skipped}, failed: {failed}",
        file=sys.stderr,
    )

    if args.commit and args.reconfigure:
        if failed:
            print("Skipping reconfigure — one or more reservations failed to import.", file=sys.stderr)
            sys.exit(1)
        try:
            api_post("/api/dnsmasq/service/reconfigure")
            print("dnsmasq reconfigured.", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print(f"Error reconfiguring dnsmasq: {e}", file=sys.stderr)
            sys.exit(1)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
