#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import time
import argparse
from config import MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CLIENT_ID

offline_devices = {}  # {coordinator: [device_names]}
device_count = 0
coordinator_devices = {}  # {coordinator: [device_names]}
retained_availability = {}  # {coordinator: {device_name: state}}
all_device_topics = {}  # {coordinator: set(device_names)} - all devices seen in topics


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
            # devices is a dict with device IDs as keys
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

    # Track all device topics (skip bridge topics)
    parts = msg.topic.split("/")
    if len(parts) >= 2 and not parts[1].startswith("bridge"):
        coordinator = parts[0]
        device_name = parts[1]

        # Track this device was seen in topics
        if coordinator not in all_device_topics:
            all_device_topics[coordinator] = set()
        all_device_topics[coordinator].add(device_name)

    # Track availability specifically for offline detection
    if "/availability" in msg.topic:
        parts = msg.topic.split("/")
        coordinator = parts[0]
        device_name = parts[1]
        payload = msg.payload.decode("utf-8")
        state = json.loads(payload).get("state", "")

        # Track retained availability messages
        if coordinator not in retained_availability:
            retained_availability[coordinator] = {}
        retained_availability[coordinator][device_name] = state

        # Track offline devices by coordinator
        if state == "offline":
            if coordinator not in offline_devices:
                offline_devices[coordinator] = []
            if device_name not in offline_devices[coordinator]:
                offline_devices[coordinator].append(device_name)
        elif state == "online":
            if (
                coordinator in offline_devices
                and device_name in offline_devices[coordinator]
            ):
                offline_devices[coordinator].remove(device_name)
                # Clean up empty coordinator entries
                if not offline_devices[coordinator]:
                    del offline_devices[coordinator]

        device_count += 1


def clear_stranded_devices(client, stranded_devices):
    """Clear stranded device retained messages by publishing empty payloads"""
    total_cleared = 0
    topics_to_clear = []

    # Callback to collect all topics for stranded devices
    def collect_topics(_client, _userdata, msg):
        topics_to_clear.append(msg.topic)

    # Temporarily replace the message callback
    original_callback = client.on_message
    client.on_message = collect_topics

    # Subscribe to each stranded device's topic tree and collect all topics
    for coordinator, devices in stranded_devices.items():
        for device in devices:
            # Subscribe to all subtopics under this device
            device_topic = f"{coordinator}/{device}/#"
            client.subscribe(device_topic)
            # Also subscribe to the base device topic (without subtopics)
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
        total_cleared += 1

    return total_cleared


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monitor and manage Zigbee offline devices"
    )
    parser.add_argument(
        "--remove-stranded",
        action="store_true",
        help="Remove stranded device retained messages",
    )
    parser.add_argument(
        "--monitoring-time",
        type=int,
        default=5,
        help="Time in seconds to monitor MQTT messages (default: 5)",
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

    print(f"Monitoring for {args.monitoring_time} seconds...")
    time.sleep(args.monitoring_time)

    client.loop_stop()

    # Find stranded devices - compare all topics seen vs coordinator's device list
    stranded_devices = {}
    for coordinator, seen_devices in all_device_topics.items():
        if coordinator in coordinator_devices:
            active_device_list = coordinator_devices[coordinator]
            stranded = [
                dev for dev in seen_devices if dev not in active_device_list
            ]
            if stranded:
                stranded_devices[coordinator] = stranded

    # Print results
    print("\n" + "=" * 60)
    print("OFFLINE DEVICES")
    print("=" * 60)

    if offline_devices:
        total_offline = sum(len(devs) for devs in offline_devices.values())
        print(f"\nFound {total_offline} offline device(s):\n")
        for coordinator, devices in offline_devices.items():
            print(f"{coordinator}:")
            for device in devices:
                print(f"  • {device}")
    else:
        print("\n✓ All devices are online!")

    print(f"\nTotal devices checked: {device_count}")

    # Print stranded devices
    print("\n" + "=" * 60)
    print("STRANDED DEVICES (retained messages, not in coordinator)")
    print("=" * 60)

    if stranded_devices:
        total_stranded = sum(len(devs) for devs in stranded_devices.values())
        print(f"\nFound {total_stranded} stranded device(s):\n")
        for coordinator, devices in stranded_devices.items():
            print(f"{coordinator}:")
            for device in devices:
                # Show availability state if we have it
                if coordinator in retained_availability and device in retained_availability[coordinator]:
                    state = retained_availability[coordinator][device]
                    print(f"  • {device} (availability: {state})")
                else:
                    print(f"  • {device}")

        # Remove stranded devices if requested
        if args.remove_stranded:
            print("\n" + "=" * 60)
            print("REMOVING STRANDED DEVICES")
            print("=" * 60 + "\n")

            cleared = clear_stranded_devices(client, stranded_devices)

            print(f"\n✓ Cleared {cleared} stranded device(s)")
            print("=" * 60)
    else:
        print("\n✓ No stranded devices found!")

    print("=" * 60)

    client.disconnect()
