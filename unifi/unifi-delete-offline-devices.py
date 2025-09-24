#!/usr/bin/env python3

import requests
import config
import datetime
import argparse
import sys


def last_seen_days_ago(last_seen):
    """Calculate days since device was last seen."""
    if not last_seen:
        return None
    last_seen_dt = datetime.datetime.fromtimestamp(last_seen)
    delta = datetime.datetime.now() - last_seen_dt
    return delta.days


def create_session():
    """Create and authenticate a UniFi session."""
    session = requests.Session()

    if not config.PASSWORD:
        raise ValueError("UNIFI_PASSWORD environment variable is required")

    login_url = f"{config.UNIFI_CONTROLLER}/api/login"
    login_data = {"username": config.USERNAME, "password": config.PASSWORD}
    response = session.post(login_url, json=login_data)
    response.raise_for_status()

    return session


def get_historical_clients(session):
    """Get all historical/configured clients."""
    url = f"{config.UNIFI_CONTROLLER}/api/s/{config.SITE}/rest/user"
    response = session.get(url)
    response.raise_for_status()
    return response.json()["data"]


def get_active_clients(session):
    """Get currently active clients."""
    url = f"{config.UNIFI_CONTROLLER}/api/s/{config.SITE}/stat/sta"
    response = session.get(url)
    response.raise_for_status()
    return response.json()["data"]


def build_device_info(historical_clients, active_clients):
    """Build comprehensive device information from historical and active data."""
    active_by_mac = {client.get("mac"): client for client in active_clients}
    all_devices = []

    for client in historical_clients:
        mac = client.get("mac")
        active_data = active_by_mac.get(mac)
        is_online = active_data is not None

        # Use active data if available, otherwise historical data
        current_ip = active_data.get("ip") if active_data else None
        last_ip = client.get("last_ip")
        uptime = active_data.get("uptime") if active_data else None
        satisfaction = active_data.get("satisfaction") if active_data else None

        # Use last_seen from active data if device is online, otherwise from historical
        last_seen = active_data.get("last_seen") if active_data else client.get("last_seen")
        disconnect_timestamp = client.get("disconnect_timestamp")

        all_devices.append({
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
                datetime.datetime.fromtimestamp(last_seen).strftime("%Y-%m-%d %H:%M:%S")
                if last_seen else "Never"
            ),
            "last_uplink_name": client.get("last_uplink_name"),
            "last_connection_network_name": client.get("last_connection_network_name"),
        })

    return all_devices


def filter_devices(devices, name_filter=None, days_threshold=30):
    """Filter devices based on name and offline threshold."""
    filtered = devices

    # Apply name filter
    if name_filter:
        filtered = [d for d in filtered if name_filter.lower() in d["name"].lower()]

    # Apply days threshold filter for offline devices
    result = []
    for device in filtered:
        if not device["is_online"]:
            if device.get("last_seen"):
                days_offline = last_seen_days_ago(device["last_seen"])
                if days_offline is not None and days_offline > days_threshold:
                    result.append(device)
            else:
                # Include devices with no last_seen (very old)
                result.append(device)

    return result


def print_device_summary(devices, name_filter=None, days_threshold=30):
    """Print summary of devices found."""
    if name_filter:
        print(f"Found {len(devices)} devices matching filter '{name_filter}' that are offline for {days_threshold}+ days:")
    else:
        print(f"Found {len(devices)} devices that are offline for {days_threshold}+ days:")

    if len(devices) > 0:
        print(f"  - All {len(devices)} devices shown are candidates for deletion")
    print()


def print_device_table(devices):
    """Print devices in a formatted table."""
    print(f"{'Name':<50} {'MAC':<18} {'Status':<8} {'Current IP':<15} {'Last Seen':<20}")
    print("-" * 115)

    for device in devices:
        current_ip = device["current_ip"] or device["last_ip"] or "N/A"
        print(f"{device['name']:<50} {device['mac']:<18} {device['status']:<8} {current_ip:<15} {device['last_seen_date']:<20}")


def get_devices_to_delete(devices, days_threshold):
    """Get list of devices that meet deletion criteria."""
    devices_to_delete = []
    for device in devices:
        if not device["is_online"] and device.get("last_seen"):
            days_offline = last_seen_days_ago(device["last_seen"])
            if days_offline is not None and days_offline > days_threshold:
                devices_to_delete.append(device)
    return devices_to_delete


def confirm_deletion(devices_to_delete, days_threshold):
    """Print deletion summary and get user confirmation."""
    print(f"\nFound {len(devices_to_delete)} devices offline for more than {days_threshold} days that will be deleted:")

    for device in devices_to_delete:
        days_offline = (
            last_seen_days_ago(device["last_seen"])
            if device.get("last_seen") else "Unknown"
        )
        print(f"  - {device['name']} ({device['mac']}) - {days_offline} days offline")

    confirm = input(f"\nAre you sure you want to delete these {len(devices_to_delete)} devices? (y/N): ")
    return confirm.lower() == "y"


def delete_device(session, mac):
    """Delete a device from UniFi controller."""
    delete_url = f"{config.UNIFI_CONTROLLER}/api/s/{config.SITE}/cmd/stamgr"
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
    except (ValueError, KeyError) as e:
        return False, f"Error parsing response: {e}"


def perform_deletions(session, devices_to_delete):
    """Delete devices and report results."""
    deleted_count = 0
    failed_count = 0

    for device in devices_to_delete:
        success, message = delete_device(session, device["mac"])
        if success:
            print(f"✓ Deleted {device['name']} ({device['mac']})")
            deleted_count += 1
        else:
            print(f"✗ Failed to delete {device['name']} ({device['mac']}): {message}")
            failed_count += 1

    print(f"\nDeletion complete: {deleted_count} deleted, {failed_count} failed")


def main():
    """Main function to orchestrate device cleanup."""
    parser = argparse.ArgumentParser(description="Find and optionally delete offline UniFi devices")
    parser.add_argument("--delete", action="store_true", help="Delete offline devices after confirmation")
    parser.add_argument("--days", type=int, default=30, help="Days offline threshold (default: 30)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--filter", type=str, help="Filter devices by name (case insensitive)")

    args = parser.parse_args()

    try:
        session = create_session()

        # Get device data
        historical_clients = get_historical_clients(session)
        active_clients = get_active_clients(session)

        if not historical_clients:
            print("No devices found.")
            return

        # Build comprehensive device info
        all_devices = build_device_info(historical_clients, active_clients)

        # Filter devices based on criteria
        filtered_devices = filter_devices(all_devices, args.filter, args.days)

        # Sort by last_seen timestamp (most recent first)
        filtered_devices.sort(key=lambda x: x.get("last_seen", 0), reverse=True)

        # Display results
        print_device_summary(filtered_devices, args.filter, args.days)
        print_device_table(filtered_devices)

        # Handle deletion if requested
        if args.delete:
            devices_to_delete = get_devices_to_delete(filtered_devices, args.days)

            if not devices_to_delete:
                print(f"\nNo devices found that are offline for more than {args.days} days.")
                return

            # Confirm deletion unless forced
            if not args.force:
                if not confirm_deletion(devices_to_delete, args.days):
                    print("Deletion cancelled.")
                    return

            perform_deletions(session, devices_to_delete)

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to UniFi controller: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            logout_url = f"{config.UNIFI_CONTROLLER}/logout"
            session.post(logout_url)
        except:
            pass  # Ignore logout errors


if __name__ == "__main__":
    main()