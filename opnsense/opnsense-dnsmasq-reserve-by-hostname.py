#!/usr/bin/env python3

import ipaddress
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


def get_leases():
    """Fetch active leases from the OPNsense dnsmasq API."""
    data = api_get("/api/dnsmasq/leases/search")
    return data.get("rows", [])


def get_existing_hosts():
    """Fetch existing dnsmasq host reservations, to avoid IP/MAC collisions."""
    data = api_post("/api/dnsmasq/settings/search_host")
    return data.get("rows", [])


def print_matches(leases):
    print(f"{'HOSTNAME':30} {'ADDRESS':16} {'HWADDR'}")
    for lease in leases:
        hostname = lease.get("hostname") or "(no hostname)"
        print(f"{hostname:30} {lease.get('address', ''):16} {lease.get('hwaddr', '')}")


def prompt_pattern():
    answer = input("Enter a substring to match against lease hostnames: ").strip()
    return answer


def prompt_start_ip():
    while True:
        answer = input(
            "\nEnter the starting IP address for reservations (or leave blank/'null' to cancel): "
        ).strip()
        if not answer or answer.lower() == "null":
            return None
        try:
            return ipaddress.IPv4Address(answer)
        except ipaddress.AddressValueError:
            print(f"'{answer}' is not a valid IPv4 address, try again.", file=sys.stderr)


def build_host_payload(lease, ip, domain):
    return {
        "host": lease.get("hostname", ""),
        "domain": domain,
        "ip": str(ip),
        "hwaddr": lease.get("hwaddr", ""),
        "descr": "",
        "local": "1",
    }


def main():
    if not config.OPNSENSE_URL or not config.OPNSENSE_API_KEY or not config.OPNSENSE_API_SECRET:
        print(
            "OPNSENSE_URL, OPNSENSE_API_KEY, and OPNSENSE_API_SECRET environment variables are required",
            file=sys.stderr,
        )
        sys.exit(1)
    domain = config.OPNSENSE_INTERNAL_DOMAIN
    if not domain:
        print(
            "No domain configured. Set OPNSENSE_INTERNAL_DOMAIN in .env — "
            "OPNsense will not reliably resolve reservations via Unbound with a blank domain.",
            file=sys.stderr,
        )
        sys.exit(1)

    global AUTH, SESSION
    AUTH = (config.OPNSENSE_API_KEY, config.OPNSENSE_API_SECRET)
    SESSION = requests.Session()

    raw_pattern = prompt_pattern()
    if not raw_pattern:
        print("Cancelled.")
        sys.exit(0)

    try:
        leases = get_leases()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching leases from OPNsense: {e}", file=sys.stderr)
        sys.exit(1)

    pattern = raw_pattern.lower()
    matches = sorted(
        (lease for lease in leases if pattern in (lease.get("hostname") or "").lower()),
        key=lambda lease: lease.get("hostname", ""),
    )

    if not matches:
        print(f"No leases found with hostname matching '{raw_pattern}'.")
        sys.exit(0)

    print(f"\n{len(matches)} lease(s) matched '{raw_pattern}':\n")
    print_matches(matches)

    missing_mac = [lease for lease in matches if not lease.get("hwaddr")]
    if missing_mac:
        print(
            f"\nWarning: {len(missing_mac)} matched lease(s) have no MAC address and will be skipped:",
            file=sys.stderr,
        )
        for lease in missing_mac:
            print(f"  {lease.get('hostname') or '(no hostname)'}", file=sys.stderr)
        matches = [lease for lease in matches if lease.get("hwaddr")]

    if not matches:
        print("\nNo eligible leases remain after filtering out missing MAC addresses.", file=sys.stderr)
        sys.exit(1)

    start_ip = prompt_start_ip()
    if start_ip is None:
        print("Cancelled.")
        sys.exit(0)

    assignments = [(lease, start_ip + i) for i, lease in enumerate(matches)]

    try:
        existing_hosts = get_existing_hosts()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing dnsmasq reservations: {e}", file=sys.stderr)
        sys.exit(1)

    existing_ips = {h.get("ip", "").lower() for h in existing_hosts if h.get("ip")}
    existing_macs = {h.get("hwaddr", "").lower() for h in existing_hosts if h.get("hwaddr")}

    lease_ips_in_use = {
        lease.get("address", "").lower()
        for lease in leases
        if lease.get("address") and lease not in matches
    }

    conflicts = []
    for lease, ip in assignments:
        ip_str = str(ip).lower()
        if ip_str in existing_ips:
            conflicts.append(f"{ip}  already has a dnsmasq reservation")
        elif ip_str in lease_ips_in_use:
            conflicts.append(f"{ip}  is currently leased to a different host")

    if conflicts:
        print("\nRefusing to proceed — IP conflicts detected:", file=sys.stderr)
        for conflict in conflicts:
            print(f"  {conflict}", file=sys.stderr)
        sys.exit(1)

    print(f"\nCreating {len(assignments)} reservation(s) starting at {start_ip}:\n")

    created, failed = 0, 0
    for lease, ip in assignments:
        hostname = lease.get("hostname") or "(no hostname)"
        mac = lease.get("hwaddr", "")

        if mac.lower() in existing_macs:
            print(f"SKIP  {hostname:30} {str(ip):16} {mac}  (MAC already reserved elsewhere)")
            continue

        payload = build_host_payload(lease, ip, domain)
        try:
            result = api_post("/api/dnsmasq/settings/add_host", {"host": payload})
            if result.get("result") == "saved":
                print(f"ADDED  {hostname:30} {str(ip):16} {mac}")
                created += 1
            else:
                print(f"FAILED {hostname:30} {str(ip):16} {mac}  {result}", file=sys.stderr)
                failed += 1
        except requests.exceptions.RequestException as e:
            print(f"FAILED {hostname:30} {str(ip):16} {mac}  {e}", file=sys.stderr)
            failed += 1

    print(f"\nCreated: {created}, failed: {failed}", file=sys.stderr)

    if failed:
        print("Skipping reconfigure — one or more reservations failed to create.", file=sys.stderr)
        sys.exit(1)

    if created:
        try:
            api_post("/api/dnsmasq/service/reconfigure")
            print("dnsmasq reconfigured.", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print(f"Error reconfiguring dnsmasq: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
