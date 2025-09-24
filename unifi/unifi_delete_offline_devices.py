import requests
import config
import datetime
import argparse
import sys


def last_seen_days_ago(last_seen):
    if not last_seen:
        return None
    last_seen_dt = datetime.datetime.fromtimestamp(last_seen)
    delta = datetime.datetime.now() - last_seen_dt
    return delta.days


def get_all_devices(session, offline_threshold_days=30):
    # Get historical/configured clients
    historical_url = f"{config.UNIFI_CONTROLLER}/api/s/{config.SITE}/rest/user"
    historical_response = session.get(historical_url)
    historical_response.raise_for_status()
    historical_clients = historical_response.json()["data"]

    # Get currently active clients
    active_url = f"{config.UNIFI_CONTROLLER}/api/s/{config.SITE}/stat/sta"
    active_response = session.get(active_url)
    active_response.raise_for_status()
    active_clients = active_response.json()["data"]

    # Create a lookup of currently active devices by MAC address
    active_by_mac = {client.get("mac"): client for client in active_clients}

    all_devices = []

    for client in historical_clients:
        mac = client.get("mac")
        active_data = active_by_mac.get(mac)

        # Determine if device is currently online
        is_online = active_data is not None

        # Use active data if available, otherwise historical data
        current_ip = active_data.get("ip") if active_data else None
        last_ip = client.get("last_ip")
        uptime = active_data.get("uptime") if active_data else None
        satisfaction = active_data.get("satisfaction") if active_data else None

        # Use last_seen from active data if device is online, otherwise from historical
        last_seen = (
            active_data.get("last_seen") if active_data else client.get("last_seen")
        )
        disconnect_timestamp = client.get("disconnect_timestamp")

        all_devices.append(
            {
                "mac": mac,
                "name": client.get("name") or client.get("hostname") or "Unknown",
                "is_online": is_online,
                "status": "Online" if is_online else "Offline",
                "current_ip": current_ip,
                "last_ip": last_ip,
                "uptime": uptime,
                "satisfaction": satisfaction,
                "last_seen": last_seen,
                "disconnect_timestamp": disconnect_timestamp,
                "last_seen_date": (
                    datetime.datetime.fromtimestamp(last_seen).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if last_seen
                    else "Never"
                ),
                "last_uplink_name": client.get("last_uplink_name"),
                "last_connection_network_name": client.get(
                    "last_connection_network_name"
                ),
            }
        )

    return all_devices


def delete_device(session, mac):
    delete_url = f"{config.UNIFI_CONTROLLER}/api/s/{config.SITE}/cmd/stamgr"
    # Ensure MAC is lowercase and properly formatted
    mac_formatted = mac.lower().replace("-", ":") if mac else None
    if not mac_formatted:
        return False, "No MAC address provided"

    payload = {"cmd": "forget-sta", "macs": [mac_formatted]}
    response = session.post(delete_url, json=payload)

    try:
        response_data = response.json()
        if response_data.get("meta", {}).get("rc") == "ok":
            return True, "Success"
        else:
            error_msg = response_data.get("meta", {}).get("msg", "Unknown error")
            return False, error_msg
    except:
        return response.ok, response.text


def main():
    parser = argparse.ArgumentParser(
        description="Find and optionally delete offline UniFi devices"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete offline devices after confirmation",
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Days offline threshold (default: 30)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )
    parser.add_argument(
        "--filter", type=str, help="Filter devices by name (case insensitive)"
    )

    args = parser.parse_args()

    session = requests.Session()

    try:
        if not config.PASSWORD:
            raise ValueError("UNIFI_PASSWORD environment variable is required")

        login_url = f"{config.UNIFI_CONTROLLER}/api/login"
        login_data = {"username": config.USERNAME, "password": config.PASSWORD}
        response = session.post(login_url, json=login_data)
        response.raise_for_status()

        all_devices = get_all_devices(session, args.days)

        if not all_devices:
            print("No devices found.")
            return

        online_devices = [d for d in all_devices if d["is_online"]]
        offline_devices = [d for d in all_devices if not d["is_online"]]

        # Apply filter if specified
        if args.filter:
            all_devices = [
                d for d in all_devices if args.filter.lower() in d["name"].lower()
            ]

        # Apply days threshold filter - only show devices that would be affected by delete
        filtered_devices = []
        for device in all_devices:
            if not device["is_online"]:
                # For offline devices, check if they exceed the days threshold
                if device.get("last_seen"):
                    days_offline = last_seen_days_ago(device["last_seen"])
                    if days_offline is not None and days_offline > args.days:
                        filtered_devices.append(device)
                else:
                    # Include devices with no last_seen (very old)
                    filtered_devices.append(device)

        all_devices = filtered_devices
        online_devices = [d for d in all_devices if d["is_online"]]
        offline_devices = [d for d in all_devices if not d["is_online"]]

        # Sort all devices by last_seen timestamp (most recent first)
        all_devices.sort(key=lambda x: x.get("last_seen", 0), reverse=True)

        if args.filter:
            print(
                f"Found {len(all_devices)} devices matching filter '{args.filter}' that are offline for {args.days}+ days:"
            )
        else:
            print(
                f"Found {len(all_devices)} devices that are offline for {args.days}+ days:"
            )
        if len(all_devices) > 0:
            print(
                f"  - All {len(all_devices)} devices shown are candidates for deletion"
            )
        print()

        print(
            f"{'Name':<50} {'MAC':<18} {'Status':<8} {'Current IP':<15} {'Last Seen':<20}"
        )
        print("-" * 115)

        for device in all_devices:
            current_ip = device["current_ip"] or device["last_ip"] or "N/A"
            print(
                f"{device['name']:<50} {device['mac']:<18} {device['status']:<8} {current_ip:<15} {device['last_seen_date']:<20}"
            )

        if args.delete:
            # Filter for devices that are actually offline and meet the days threshold
            devices_to_delete = []
            for device in all_devices:
                if not device["is_online"]:
                    # Calculate days offline from last_seen
                    if device.get("last_seen"):
                        days_offline = last_seen_days_ago(device["last_seen"])
                        if days_offline is not None and days_offline > args.days:
                            devices_to_delete.append(device)

            if not devices_to_delete:
                print(
                    f"\nNo devices found that are offline for more than {args.days} days."
                )
                return

            print(
                f"\nFound {len(devices_to_delete)} devices offline for more than {args.days} days that will be deleted:"
            )
            for device in devices_to_delete:
                days_offline = (
                    last_seen_days_ago(device["last_seen"])
                    if device.get("last_seen")
                    else "Unknown"
                )
                print(
                    f"  - {device['name']} ({device['mac']}) - {days_offline} days offline"
                )

            if not args.force:
                confirm = input(
                    f"\nAre you sure you want to delete these {len(devices_to_delete)} devices? (y/N): "
                )
                if confirm.lower() != "y":
                    print("Deletion cancelled.")
                    return

            deleted_count = 0
            failed_count = 0

            for device in devices_to_delete:
                success, message = delete_device(session, device["mac"])
                if success:
                    print(f"✓ Deleted {device['name']} ({device['mac']})")
                    deleted_count += 1
                else:
                    print(
                        f"✗ Failed to delete {device['name']} ({device['mac']}): {message}"
                    )
                    failed_count += 1

            print(
                f"\nDeletion complete: {deleted_count} deleted, {failed_count} failed"
            )

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to UniFi controller: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logout_url = f"{config.UNIFI_CONTROLLER}/logout"
        session.post(logout_url)


if __name__ == "__main__":
    main()
