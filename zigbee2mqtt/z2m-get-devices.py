#!/usr/bin/env python3

import json
import sys
import time
import argparse
import smtplib
from email.mime.text import MIMEText
import paho.mqtt.client as paho
import config


class ZigbeeDeviceCollector:
    """Collect and display Zigbee device information via MQTT."""

    def __init__(self, bridges):
        self.bridges = bridges
        self.devices = {}  # bridge -> {device_id: device_info}
        self.availability = {}  # bridge -> {device_name: status}
        self.bridge_info_received = set()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT connection."""
        if rc == 0:
            print("Connected to MQTT broker", file=sys.stderr)
        else:
            print(f"Failed to connect to MQTT broker: {rc}", file=sys.stderr)
            sys.exit(1)

    def on_message(self, client, userdata, message):
        """Process MQTT messages."""
        try:
            topic_parts = message.topic.split("/")
            bridge_name = topic_parts[0]
            data = json.loads(message.payload.decode())

            # Handle bridge/devices messages (full device list)
            if len(topic_parts) >= 3 and topic_parts[1] == "bridge" and topic_parts[2] == "devices":
                if isinstance(data, list):
                    self.devices[bridge_name] = data
                    self.bridge_info_received.add(bridge_name)
                    print(f"Received device list from {bridge_name} ({len(data)} devices)", file=sys.stderr)

            # Handle availability messages
            elif len(topic_parts) >= 3 and topic_parts[2] == "availability":
                device_name = topic_parts[1]
                if bridge_name not in self.availability:
                    self.availability[bridge_name] = {}
                status = data.get("state", "unknown")
                self.availability[bridge_name][device_name] = status

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON message: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)

    def collect_devices(self, timeout=5):
        """Connect to MQTT and collect device information."""
        if not all([config.MQTT_HOST, config.MQTT_USERNAME, config.MQTT_PASSWORD]):
            print("Error: Missing MQTT configuration. Check your .env file.", file=sys.stderr)
            sys.exit(1)

        client = paho.Client(client_id="z2m-device-collector", callback_api_version=paho.CallbackAPIVersion.VERSION2)
        client.username_pw_set(username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        try:
            client.connect(config.MQTT_HOST, config.MQTT_PORT)
            client.loop_start()

            # Subscribe to bridge devices and availability topics for all bridges
            topics = []
            for bridge in self.bridges:
                topics.append((f"{bridge}/bridge/devices", 0))
                topics.append((f"{bridge}/+/availability", 0))
            client.subscribe(topics)

            # Wait for data collection
            print(f"Collecting device data for {timeout} seconds...", file=sys.stderr)
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                # Check if we have info from all bridges
                if self.bridge_info_received == set(self.bridges):
                    # Give a bit more time for availability messages
                    time.sleep(1)
                    break
                time.sleep(0.1)

        except Exception as e:
            print(f"Error connecting to MQTT broker: {e}", file=sys.stderr)
            return False
        finally:
            try:
                client.disconnect()
                client.loop_stop()
            except:
                pass

        return True

    def get_merged_devices(self):
        """Merge device info with availability status."""
        merged = []

        for bridge, devices in self.devices.items():
            bridge_availability = self.availability.get(bridge, {})

            for device in devices:
                friendly_name = device.get('friendly_name', 'Unknown')
                ieee_address = device.get('ieee_address', 'Unknown')
                availability = bridge_availability.get(friendly_name, 'unknown')

                # Get model from definition if available, fallback to model_id
                definition = device.get('definition') or {}
                model = definition.get('model') or device.get('model_id') or 'Unknown'
                description = definition.get('description', '')

                merged.append({
                    'bridge': bridge,
                    'ieee_address': ieee_address,
                    'friendly_name': friendly_name,
                    'type': device.get('type', 'Unknown'),
                    'model': model,
                    'description': description,
                    'manufacturer': device.get('manufacturer', ''),
                    'availability': availability,
                    'details': device
                })

        return merged

    def print_devices(self, devices, output_format='table', show_details=False, offline_only=False):
        """Print device information in specified format."""
        if offline_only:
            devices = [d for d in devices if d['availability'] == 'offline']

        if not devices:
            if offline_only:
                print("No offline devices found.")
            else:
                print("No devices found.")
            return

        if output_format == 'json':
            if show_details:
                print(json.dumps(devices, indent=2))
            else:
                # Exclude details from JSON output unless requested
                simplified = [{k: v for k, v in d.items() if k != 'details'} for d in devices]
                print(json.dumps(simplified, indent=2))
            return

        if output_format == 'csv':
            print("Bridge,IEEE_Address,Friendly_Name,Type,Model,Manufacturer,Availability")
            for device in devices:
                print(f"{device['bridge']},{device['ieee_address']},{device['friendly_name']},"
                      f"{device['type']},{device['model']},{device['manufacturer']},{device['availability']}")
            return

        # Table format - calculate column widths based on data
        col_widths = {
            'bridge': max(len('Bridge'), max(len(d['bridge']) for d in devices)),
            'friendly_name': max(len('Friendly Name'), max(len(d['friendly_name']) for d in devices)),
            'type': max(len('Type'), max(len(d['type']) for d in devices)),
            'model': max(len('Model'), max(len(d['model']) for d in devices)),
            'status': max(len('Status'), max(len(d['availability']) for d in devices)),
        }

        # Print header
        header = (f"{'Bridge':<{col_widths['bridge']}}  "
                  f"{'Friendly Name':<{col_widths['friendly_name']}}  "
                  f"{'Type':<{col_widths['type']}}  "
                  f"{'Model':<{col_widths['model']}}  "
                  f"{'Status':<{col_widths['status']}}")
        print(f"\n{header}")
        print("-" * len(header))

        for device in devices:
            status = device['availability']
            # Highlight offline devices
            if status == 'offline':
                status_display = f"\033[91m{status:<{col_widths['status']}}\033[0m"
            elif status == 'online':
                status_display = f"\033[92m{status:<{col_widths['status']}}\033[0m"
            else:
                status_display = f"{status:<{col_widths['status']}}"

            print(f"{device['bridge']:<{col_widths['bridge']}}  "
                  f"{device['friendly_name']:<{col_widths['friendly_name']}}  "
                  f"{device['type']:<{col_widths['type']}}  "
                  f"{device['model']:<{col_widths['model']}}  "
                  f"{status_display}")

            if show_details:
                print("  Details:")
                for key, value in device['details'].items():
                    if key not in ['friendly_name', 'type', 'model_id']:
                        print(f"    {key}: {value}")
                print()

        print(f"\nTotal: {len(devices)} devices")

    def send_email_notification(self, offline_devices):
        """Send email notification about offline devices."""
        if not all([config.SMTP_HOST, config.FROM_EMAIL, config.TO_EMAIL]):
            print("Error: Missing email configuration. Check your .env file.", file=sys.stderr)
            return False

        try:
            subject = "Zigbee devices offline"
            body_lines = ["The following Zigbee devices are offline:\n"]

            for device in offline_devices:
                body_lines.append(f"• {device['bridge']} - {device['friendly_name']}")

            body = "\n".join(body_lines)

            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = config.FROM_EMAIL
            msg['To'] = config.TO_EMAIL

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.send_message(msg)

            print(f"Email notification sent to {config.TO_EMAIL}")
            return True

        except Exception as e:
            print(f"Error sending email notification: {e}", file=sys.stderr)
            return False


def main():
    """Main function to collect and display Zigbee devices."""
    # Build bridge names from config (e.g., ['11', '15'] -> ['zigbee11', 'zigbee15'])
    default_bridges = [f"zigbee{instance.strip()}" for instance in config.Z2M_INSTANCES]

    parser = argparse.ArgumentParser(description="Collect Zigbee device information via MQTT")
    parser.add_argument("--format", "-f", choices=['table', 'csv', 'json'],
                        default='table', help="Output format")
    parser.add_argument("--details", "-d", action="store_true",
                        help="Show detailed device information")
    parser.add_argument("--timeout", "-t", type=int, default=5,
                        help="Timeout in seconds (default: 5)")
    parser.add_argument("--filter", help="Filter devices by name (case insensitive)")
    parser.add_argument("--offline", "-o", action="store_true",
                        help="Show only offline devices")
    parser.add_argument("--email", "-e", action="store_true",
                        help="Send email notification if offline devices found")
    parser.add_argument("--bridges", "-b", nargs="+", default=default_bridges,
                        help=f"Bridges to query (default: {' '.join(default_bridges)})")

    args = parser.parse_args()

    collector = ZigbeeDeviceCollector(args.bridges)

    try:
        if collector.collect_devices(timeout=args.timeout):
            devices = collector.get_merged_devices()

            # Apply name filter if specified
            if args.filter:
                devices = [d for d in devices
                           if args.filter.lower() in d['friendly_name'].lower()]

            # Get offline devices for email
            offline_devices = [d for d in devices if d['availability'] == 'offline']

            # Display results
            collector.print_devices(devices, args.format, args.details, args.offline)

            # Send email notification if requested and offline devices found
            if args.email and offline_devices:
                collector.send_email_notification(offline_devices)

            # Exit with error code if showing offline only and devices found
            if args.offline and offline_devices:
                sys.exit(1)

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
