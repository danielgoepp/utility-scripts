#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
from config import MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CLIENT_ID

devices_seen = {}  # {coordinator: set(device_names)}


def on_connect(client, userdata, flags, rc, properties=None):
    client.subscribe("zigbee15/#")
    client.subscribe("zigbee11/#")
    print("Connected and subscribed to zigbee15/# and zigbee11/#")


def on_message(client, userdata, msg):
    # Extract coordinator and device name from topic
    parts = msg.topic.split("/")
    if len(parts) >= 2:
        coordinator = parts[0]
        device = parts[1]

        # Track unique devices per coordinator
        if coordinator not in devices_seen:
            devices_seen[coordinator] = set()
        devices_seen[coordinator].add(device)


if __name__ == "__main__":
    client = mqtt.Client(
        client_id=f"{MQTT_CLIENT_ID}_list_devices",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    print("Connecting to MQTT broker...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    print("Monitoring for 5 seconds...")
    time.sleep(5)

    client.loop_stop()
    client.disconnect()

    # Print results
    print("\n" + "=" * 60)
    print("DEVICES FOUND IN MQTT TOPICS")
    print("=" * 60)

    for coordinator in sorted(devices_seen.keys()):
        devices = sorted(devices_seen[coordinator])
        print(f"\n{coordinator} ({len(devices)} devices):")
        for device in devices:
            print(f"  • {device}")

    print("\n" + "=" * 60)
    total_devices = sum(len(devs) for devs in devices_seen.values())
    print(f"Total devices across all coordinators: {total_devices}")
    print("=" * 60)
