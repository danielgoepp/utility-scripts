#!/usr/bin/env python3

import argparse
import csv
import datetime
import json
import sys

import requests

import config

CLIENT_CSV_FIELDS = [
    "name",
    "mac",
    "ip",
    "is_wired",
    "network",
    "essid",
    "ap_mac",
    "sw_mac",
    "sw_port",
    "signal",
    "rx_rate",
    "tx_rate",
    "uptime",
    "first_seen_date",
    "last_seen_date",
]


def create_session():
    """Create a UniFi session authenticated via local API key."""
    if not config.UNIFI_LOCAL_API_KEY:
        raise ValueError("UNIFI_LOCAL_API_KEY environment variable is required")

    session = requests.Session()
    session.headers.update({"X-API-Key": config.UNIFI_LOCAL_API_KEY})
    return session


def get_active_clients(session):
    """Get currently active (online) clients."""
    url = f"{config.UNIFI_CONTROLLER}/proxy/network/api/s/{config.SITE}/stat/sta"
    response = session.get(url)
    response.raise_for_status()
    return response.json()["data"]


def build_client_info(active_clients):
    """Normalize raw client data into a consistent set of fields."""
    clients = []

    for client in active_clients:
        first_seen = client.get("first_seen")
        last_seen = client.get("last_seen")
        clients.append({
            "name": client.get("name") or client.get("hostname") or "Unknown",
            "mac": client.get("mac"),
            "ip": client.get("ip"),
            "is_wired": client.get("is_wired", False),
            "network": client.get("network"),
            "essid": client.get("essid"),
            "ap_mac": client.get("ap_mac"),
            "sw_mac": client.get("sw_mac"),
            "sw_port": client.get("sw_port"),
            "signal": client.get("signal"),
            "rx_rate": client.get("rx_rate"),
            "tx_rate": client.get("tx_rate"),
            "uptime": client.get("uptime"),
            "first_seen": first_seen,
            "first_seen_date": (
                datetime.datetime.fromtimestamp(first_seen).strftime("%Y-%m-%d %H:%M:%S")
                if first_seen else "Unknown"
            ),
            "last_seen": last_seen,
            "last_seen_date": (
                datetime.datetime.fromtimestamp(last_seen).strftime("%Y-%m-%d %H:%M:%S")
                if last_seen else "Unknown"
            ),
        })

    return clients


def print_client_table(clients):
    """Print clients in a formatted table."""
    print(f"{'Name':<35} {'MAC':<18} {'IP':<15} {'Type':<7} {'Network':<20} {'ESSID/Port':<15}")
    print("-" * 115)

    for client in clients:
        conn_type = "Wired" if client["is_wired"] else "Wireless"
        detail = client["sw_port"] if client["is_wired"] else client["essid"]
        print(
            f"{client['name']:<35} {client['mac']:<18} {client['ip'] or 'N/A':<15} "
            f"{conn_type:<7} {client['network'] or 'N/A':<20} {str(detail) or 'N/A':<15}"
        )


def print_client_csv(clients):
    """Print clients as CSV."""
    writer = csv.DictWriter(sys.stdout, fieldnames=CLIENT_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for client in clients:
        writer.writerow(client)


def main():
    """Main function to fetch and display currently online UniFi clients."""
    parser = argparse.ArgumentParser(description="Dump all currently online UniFi client devices")
    parser.add_argument(
        "--format", choices=["table", "csv", "json"], default="table",
        help="Output format (default: table)",
    )
    parser.add_argument("--filter", type=str, help="Filter clients by name (case insensitive)")
    args = parser.parse_args()

    try:
        session = create_session()
        active_clients = get_active_clients(session)
        clients = build_client_info(active_clients)

        if args.filter:
            clients = [c for c in clients if args.filter.lower() in c["name"].lower()]

        clients.sort(key=lambda c: c["name"].lower())

        if args.format == "json":
            print(json.dumps(clients, indent=4))
        elif args.format == "csv":
            print_client_csv(clients)
        else:
            print(f"Found {len(clients)} online client(s):\n")
            print_client_table(clients)

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            print(
                f"Error connecting to UniFi controller: {e} — the local API key "
                "(UNIFI_LOCAL_API_KEY) is missing, invalid, or unauthorized",
                file=sys.stderr,
            )
        else:
            print(f"Error connecting to UniFi controller: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to UniFi controller: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
