#!/usr/bin/env python3

import json
import sys
import time
import argparse
import paho.mqtt.client as paho
import config


class ZigbeeDeviceCollector:
    """Collect and display Zigbee device information via MQTT."""

    def __init__(self):
        self.devices_collected = False
        self.device_data = None

    def on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            print("Connected to MQTT broker", file=sys.stderr)
        else:
            print(f"Failed to connect to MQTT broker: {rc}", file=sys.stderr)
            sys.exit(1)

    def on_message(self, client, userdata, message):
        """Process MQTT message containing device information."""
        try:
            print(f"Received data from topic: {message.topic}", file=sys.stderr)
            data = json.loads(message.payload.decode())

            if "config" in data and "devices" in data["config"]:
                self.device_data = data["config"]["devices"]
                self.devices_collected = True
            else:
                print("Warning: Message does not contain expected device config", file=sys.stderr)

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON message: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)

    def collect_devices(self, timeout=5):
        """Connect to MQTT and collect device information."""
        if not all([config.MQTT_HOST, config.MQTT_USERNAME, config.MQTT_PASSWORD]):
            print("Error: Missing MQTT configuration. Check your .env file.", file=sys.stderr)
            sys.exit(1)

        client = paho.Client(client_id="z2m-device-collector", callback_api_version=paho.CallbackAPIVersion.VERSION1)
        client.username_pw_set(username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        try:
            client.connect(config.MQTT_HOST, config.MQTT_PORT)
            client.loop_start()

            # Subscribe to bridge info topic
            client.subscribe("zigbee15/bridge/info")

            # Wait for data collection
            start_time = time.time()
            while not self.devices_collected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.devices_collected:
                print(f"Timeout: No device data received within {timeout} seconds", file=sys.stderr)
                return None

        except Exception as e:
            print(f"Error connecting to MQTT broker: {e}", file=sys.stderr)
            return None
        finally:
            try:
                client.disconnect()
                client.loop_stop()
            except:
                pass

        return self.device_data

    def print_devices(self, devices, output_format='table', show_details=False):
        """Print device information in specified format."""
        if not devices:
            print("No devices found.")
            return

        if output_format == 'json':
            print(json.dumps(devices, indent=2))
            return

        if output_format == 'csv':
            print("Device_ID,Friendly_Name,Type,Model")
            for device_id, device_info in devices.items():
                friendly_name = device_info.get('friendly_name', 'Unknown')
                device_type = device_info.get('type', 'Unknown')
                model = device_info.get('model_id', 'Unknown')
                print(f"{device_id},{friendly_name},{device_type},{model}")
            return

        # Table format
        print(f"{'Device ID':<20} {'Friendly Name':<30} {'Type':<15} {'Model':<20}")
        print("-" * 85)

        for device_id, device_info in devices.items():
            friendly_name = device_info.get('friendly_name', 'Unknown')
            device_type = device_info.get('type', 'Unknown')
            model = device_info.get('model_id', 'Unknown')

            print(f"{device_id:<20} {friendly_name:<30} {device_type:<15} {model:<20}")

            if show_details:
                print("  Details:")
                for key, value in device_info.items():
                    if key not in ['friendly_name', 'type', 'model_id']:
                        print(f"    {key}: {value}")
                print()


def main():
    """Main function to collect and display Zigbee devices."""
    parser = argparse.ArgumentParser(description="Collect Zigbee device information via MQTT")
    parser.add_argument("--format", "-f", choices=['table', 'csv', 'json'],
                       default='table', help="Output format")
    parser.add_argument("--details", "-d", action="store_true",
                       help="Show detailed device information")
    parser.add_argument("--timeout", "-t", type=int, default=5,
                       help="Timeout in seconds (default: 5)")
    parser.add_argument("--filter", help="Filter devices by name (case insensitive)")

    args = parser.parse_args()

    collector = ZigbeeDeviceCollector()

    try:
        print("Collecting device information...", file=sys.stderr)
        devices = collector.collect_devices(timeout=args.timeout)

        if devices:
            # Apply filter if specified
            if args.filter:
                filtered_devices = {k: v for k, v in devices.items()
                                  if args.filter.lower() in v.get('friendly_name', '').lower()}
                devices = filtered_devices

            collector.print_devices(devices, args.format, args.details)
        else:
            print("Failed to collect device information.", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()