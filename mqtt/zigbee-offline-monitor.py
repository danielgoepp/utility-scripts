#!/usr/bin/env python3

"""
Zigbee Offline Device Monitor

This script monitors Zigbee2MQTT coordinators to detect and manage offline devices and
stranded retained MQTT messages. It connects to multiple Zigbee2MQTT coordinators via
MQTT, monitors device availability status, and identifies devices that no longer exist
in the coordinator configuration but still have retained messages in MQTT.

Key Features:
- Monitors availability status for all Zigbee devices across multiple coordinators
- Identifies offline devices (devices with "offline" availability state)
- Detects stranded devices (retained MQTT messages for devices removed from coordinator)
- Optional cleanup mode (--remove-stranded) to clear retained messages from stranded devices

Usage:
    python zigbee-offline-monitor.py              # Monitor and prompt to remove stranded devices
    python zigbee-offline-monitor.py --remove-stranded  # Automatically remove stranded devices
    python zigbee-offline-monitor.py --no-interactive  # Monitor only, no prompts or removal

Configuration:
    Requires environment variables in .env (loaded via config.py):
    - MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CLIENT_ID
"""

import paho.mqtt.client as mqtt
import json
import time
import argparse
from collections import defaultdict
from config import MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CLIENT_ID

MONITORING_TIME = 5

# Global state tracking
device_count = 0
coordinator_devices = {}  # {coordinator: [device_names]}
offline_devices = defaultdict(set)  # {coordinator: {device_names}}
retained_availability = defaultdict(dict)  # {coordinator: {device_name: state}}
all_device_topics = defaultdict(set)  # {coordinator: {device_names}}


def on_connect(client, userdata, flags, rc, properties=None):
    client.subscribe("zigbee15/#")
    client.subscribe("zigbee11/#")


def on_message(client, userdata, msg):
    global device_count

    # Parse bridge/info to get device list from coordinator
    if msg.topic.endswith("/bridge/info"):
        coordinator = msg.topic.split("/")[0]
        try:
            info = json.loads(msg.payload.decode("utf-8"))
            # Extract device friendly names from the config
            if "config" in info and "devices" in info["config"]:
                devices_dict = info["config"]["devices"]
                if isinstance(devices_dict, dict):
                    device_names = [
                        dev.get("friendly_name")
                        for dev in devices_dict.values()
                        if isinstance(dev, dict) and dev.get("friendly_name")
                    ]
                    coordinator_devices[coordinator] = device_names
                    print(f"Loaded {len(device_names)} devices from {coordinator}")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing bridge/info for {coordinator}: {e}")
        return

    # Parse topic once
    parts = msg.topic.split("/")
    if len(parts) < 2:
        return

    coordinator = parts[0]
    device_name = parts[1]

    # Track all device topics (skip bridge topics)
    if not device_name.startswith("bridge"):
        all_device_topics[coordinator].add(device_name)

    # Track availability specifically for offline detection
    if msg.topic.endswith("/availability"):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            state = payload.get("state", "")

            # Track retained availability messages
            retained_availability[coordinator][device_name] = state

            # Track offline devices by coordinator
            if state == "offline":
                offline_devices[coordinator].add(device_name)
            elif state == "online":
                offline_devices[coordinator].discard(device_name)

            device_count += 1
        except (json.JSONDecodeError, KeyError):
            pass


def clear_stranded_devices(client, stranded_devices):
    """Clear stranded device retained messages by publishing empty payloads"""
    topics_to_clear = []

    # Build set of valid topic prefixes for filtering
    valid_prefixes = set()
    for coordinator, devices in stranded_devices.items():
        for device in devices:
            valid_prefixes.add(f"{coordinator}/{device}/")
            valid_prefixes.add(f"{coordinator}/{device}")

    # Callback to collect all topics for stranded devices
    def collect_topics(_client, _userdata, msg):
        # Only collect topics that match our stranded devices
        topic = msg.topic
        if any(topic == prefix or topic.startswith(prefix + "/") for prefix in valid_prefixes):
            topics_to_clear.append(topic)

    # Temporarily replace the message callback
    original_callback = client.on_message
    client.on_message = collect_topics

    # Subscribe to each stranded device's topic tree
    for coordinator, devices in stranded_devices.items():
        for device in devices:
            client.subscribe(f"{coordinator}/{device}/#")
            client.subscribe(f"{coordinator}/{device}")

    # Give time to receive all retained messages
    client.loop_start()
    time.sleep(2)
    client.loop_stop()

    # Restore original callback
    client.on_message = original_callback

    # Unsubscribe from device topics
    for coordinator, devices in stranded_devices.items():
        for device in devices:
            client.unsubscribe(f"{coordinator}/{device}/#")
            client.unsubscribe(f"{coordinator}/{device}")

    # Clear all collected topics
    for topic in topics_to_clear:
        print(f"Clearing retained message: {topic}")
        client.publish(topic, payload=None, retain=True)

    return len(topics_to_clear)


def print_section(title, items=None, item_formatter=None):
    """Print a formatted section with optional items"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    if items:
        total = sum(len(devs) for devs in items.values())
        print(f"\nFound {total} {title.lower()}:\n")
        for coordinator, devices in items.items():
            print(f"{coordinator}:")
            for device in sorted(devices):
                if item_formatter:
                    print(item_formatter(coordinator, device))
                else:
                    print(f"  • {device}")
    else:
        print(f"\n✓ No {title.lower()} found!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monitor and manage Zigbee offline devices"
    )
    parser.add_argument(
        "--remove-stranded",
        action="store_true",
        help="Automatically remove stranded device retained messages without prompting",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive prompts (monitor only, no removal)",
    )
    args = parser.parse_args()

    client = mqtt.Client(
        client_id=f"{MQTT_CLIENT_ID}_offline_monitor",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT broker...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    print(f"Monitoring for {MONITORING_TIME} seconds...")
    time.sleep(MONITORING_TIME)

    client.loop_stop()

    # Find stranded devices - compare all topics seen vs coordinator's device list
    stranded_devices = {
        coordinator: [
            dev
            for dev in seen_devices
            if dev not in coordinator_devices.get(coordinator, [])
        ]
        for coordinator, seen_devices in all_device_topics.items()
        if coordinator in coordinator_devices
    }
    # Remove empty entries
    stranded_devices = {k: v for k, v in stranded_devices.items() if v}

    # Print offline devices
    print_section("OFFLINE DEVICES", offline_devices if offline_devices else None)
    print(f"\nTotal devices checked: {device_count}")

    # Print stranded devices with availability state
    if stranded_devices:

        def format_stranded(coordinator, device):
            state = retained_availability.get(coordinator, {}).get(device, "")
            if state:
                return f"  • {device} (availability: {state})"
            return f"  • {device}"

        print_section(
            "STRANDED DEVICES (retained messages, not in coordinator)",
            stranded_devices,
            format_stranded,
        )

        # Determine if we should remove stranded devices
        should_remove = False

        if args.remove_stranded:
            # Automatic mode - remove without prompting
            should_remove = True
        elif not args.no_interactive:
            # Interactive mode - prompt the user
            try:
                response = input("\nRemove stranded devices? [y/N]: ").strip().lower()
                should_remove = response in ['y', 'yes']
            except (EOFError, KeyboardInterrupt):
                print("\nSkipping removal.")
                should_remove = False

        # Remove stranded devices if confirmed
        if should_remove:
            print("\n" + "=" * 60)
            print("REMOVING STRANDED DEVICES")
            print("=" * 60 + "\n")

            cleared = clear_stranded_devices(client, stranded_devices)

            print(f"\n✓ Cleared {cleared} retained message(s)")
            print("=" * 60)
    else:
        print_section("STRANDED DEVICES (retained messages, not in coordinator)", None)

    print("=" * 60)

    client.disconnect()
