#!/usr/bin/env python3
"""Monitor a Zigbee2MQTT device and display state changes between messages."""

import argparse
import json
import sys
from datetime import datetime

import paho.mqtt.client as paho

import config


def parse_args():
    parser = argparse.ArgumentParser(
        description="Monitor a Zigbee2MQTT device and display state changes between messages."
    )
    parser.add_argument(
        "device",
        help="Friendly name of the device to monitor (e.g. 'Makerspace Test Plug')",
    )
    parser.add_argument(
        "-b",
        "--bridge",
        default="zigbee11",
        help="Bridge/coordinator name (default: zigbee11)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show full state on every message, not just changes",
    )
    return parser.parse_args()


def format_value(value):
    """Format a value for display."""
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    return str(value)


def diff_state(old, new):
    """Return dict of changed keys with (old_value, new_value) tuples."""
    changes = {}
    all_keys = set(list(old.keys()) + list(new.keys()))
    for key in sorted(all_keys):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            changes[key] = (old_val, new_val)
    return changes


def main():
    args = parse_args()
    topic = f"{args.bridge}/{args.device}"
    last_state = {}
    message_count = 0

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"Connected to {config.MQTT_HOST}:{config.MQTT_PORT}")
            print(f"Subscribing to: {topic}")
            print("-" * 60)
            client.subscribe(topic, qos=0)
        else:
            print(f"Connection failed with code {rc}", file=sys.stderr)
            sys.exit(1)

    def on_message(client, userdata, message):
        nonlocal last_state, message_count

        try:
            data = json.loads(message.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Non-JSON payload: {message.payload}")
            return

        message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if args.all or not last_state:
            label = "Initial state" if not last_state else f"Full state (msg #{message_count})"
            print(f"[{timestamp}] {label}:")
            for key in sorted(data.keys()):
                print(f"  {key}: {format_value(data[key])}")
            print()
        else:
            changes = diff_state(last_state, data)
            if changes:
                print(f"[{timestamp}] Message #{message_count} - {len(changes)} field(s) changed:")
                for key, (old_val, new_val) in changes.items():
                    if old_val is None:
                        print(f"  + {key}: {format_value(new_val)}")
                    elif new_val is None:
                        print(f"  - {key}: {format_value(old_val)}")
                    else:
                        print(f"  ~ {key}: {format_value(old_val)} -> {format_value(new_val)}")
                print()
            else:
                print(f"[{timestamp}] Message #{message_count} - no changes (duplicate)")
                print()

        last_state = data

    client = paho.Client(client_id="z2m-device-monitor")
    client.username_pw_set(
        username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        if not config.MQTT_HOST or not config.MQTT_PORT:
            print("Error: MQTT_HOST and MQTT_PORT must be configured in .env", file=sys.stderr)
            sys.exit(1)
        client.connect(config.MQTT_HOST, config.MQTT_PORT)
        print(f"Monitoring '{args.device}' on {args.bridge} (Ctrl+C to stop)...")
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\nStopped after {message_count} messages.")
        client.disconnect()


if __name__ == "__main__":
    main()
