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
        self.devices = {}  # bridge -> [device_info]
        self.availability = {}  # bridge -> {device_name: status}
        self.bridge_info_received = set()
        self.all_device_topics = {}  # bridge -> set(device_names) - all topics seen
        self.client = None

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

            # Track all device topics for stranded detection (skip bridge topics)
            if len(topic_parts) >= 2 and not topic_parts[1].startswith("bridge"):
                if bridge_name not in self.all_device_topics:
                    self.all_device_topics[bridge_name] = set()
                self.all_device_topics[bridge_name].add(topic_parts[1])

            # Skip non-JSON payloads
            if not message.payload:
                return

            try:
                data = json.loads(message.payload.decode())
            except json.JSONDecodeError:
                return

            # Handle bridge/devices messages (full device list)
            if len(topic_parts) >= 3 and topic_parts[1] == "bridge" and topic_parts[2] == "devices":
                if isinstance(data, list) and bridge_name not in self.bridge_info_received:
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

        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)

    def collect_devices(self, scan_stranded=False):
        """Connect to MQTT and collect device information."""
        if not all([config.MQTT_HOST, config.MQTT_USERNAME, config.MQTT_PASSWORD]):
            print("Error: Missing MQTT configuration. Check your .env file.", file=sys.stderr)
            sys.exit(1)

        self.client = paho.Client(client_id="z2m-device-collector", callback_api_version=paho.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            self.client.connect(config.MQTT_HOST, config.MQTT_PORT)
            self.client.loop_start()

            # Subscribe to topics
            topics = []
            for bridge in self.bridges:
                topics.append((f"{bridge}/bridge/devices", 0))
                topics.append((f"{bridge}/+/availability", 0))
                # For stranded detection, subscribe to all topics under each bridge
                if scan_stranded:
                    topics.append((f"{bridge}/#", 0))
            self.client.subscribe(topics)

            # Wait for data collection
            timeout = config.Z2M_TIMEOUT
            print(f"Collecting device data for {timeout} seconds...", file=sys.stderr)
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                # Check if we have info from all bridges
                if self.bridge_info_received == set(self.bridges):
                    # Give more time for stranded detection or availability messages
                    extra_time = 2 if scan_stranded else 1
                    time.sleep(extra_time)
                    break
                time.sleep(0.1)

        except Exception as e:
            print(f"Error connecting to MQTT broker: {e}", file=sys.stderr)
            return False

        return True

    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            try:
                self.client.disconnect()
                self.client.loop_stop()
            except:
                pass

    def get_merged_devices(self):
        """Merge device info with availability status."""
        merged = []

        for bridge, devices in self.devices.items():
            bridge_availability = self.availability.get(bridge, {})

            for device in devices:
                friendly_name = device.get('friendly_name', 'Unknown')

                # Skip Coordinator - it's not a real device
                if friendly_name == 'Coordinator':
                    continue

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
                })

        return merged

    def get_stranded_devices(self):
        """Find stranded devices - MQTT topics for devices not in coordinator config."""
        stranded = {}

        for bridge, seen_topics in self.all_device_topics.items():
            if bridge not in self.devices:
                continue

            # Get list of known device friendly names, excluding Coordinator
            # Coordinators shouldn't have device topics (like availability), so any
            # Coordinator/* topics are stranded and should be cleaned up
            known_devices = set()
            for device in self.devices[bridge]:
                friendly_name = device.get('friendly_name')
                if friendly_name and friendly_name != 'Coordinator':
                    known_devices.add(friendly_name)

            # Find topics that don't match any known device
            stranded_in_bridge = []
            for topic_device in seen_topics:
                if topic_device not in known_devices:
                    # Get availability state if we have it
                    state = self.availability.get(bridge, {}).get(topic_device, '')
                    stranded_in_bridge.append({
                        'bridge': bridge,
                        'device': topic_device,
                        'availability': state
                    })

            if stranded_in_bridge:
                stranded[bridge] = stranded_in_bridge

        # Remove empty entries
        stranded = {k: v for k, v in stranded.items() if v}

        return stranded

    def remove_stranded_devices(self, stranded_devices):
        """Remove stranded device retained messages by publishing empty payloads."""
        if not self.client:
            print("Error: Not connected to MQTT broker", file=sys.stderr)
            return 0

        topics_to_clear = []

        # Build set of valid topic prefixes for filtering
        valid_prefixes = set()
        for bridge, devices in stranded_devices.items():
            for device_info in devices:
                device = device_info['device']
                valid_prefixes.add(f"{bridge}/{device}/")
                valid_prefixes.add(f"{bridge}/{device}")

        # Callback to collect all topics for stranded devices
        collected_topics = []

        def collect_topics(client, userdata, msg):
            topic = msg.topic
            if any(topic == prefix or topic.startswith(prefix) for prefix in valid_prefixes):
                collected_topics.append(topic)

        # Temporarily replace the message callback
        original_callback = self.client.on_message
        self.client.on_message = collect_topics

        # Subscribe to each stranded device's topic tree
        for bridge, devices in stranded_devices.items():
            for device_info in devices:
                device = device_info['device']
                self.client.subscribe(f"{bridge}/{device}/#")
                self.client.subscribe(f"{bridge}/{device}")

        # Give time to receive all retained messages
        time.sleep(2)

        # Restore original callback
        self.client.on_message = original_callback

        # Unsubscribe from device topics
        for bridge, devices in stranded_devices.items():
            for device_info in devices:
                device = device_info['device']
                self.client.unsubscribe(f"{bridge}/{device}/#")
                self.client.unsubscribe(f"{bridge}/{device}")

        # Clear all collected topics
        for topic in collected_topics:
            print(f"Clearing retained message: {topic}")
            self.client.publish(topic, payload=None, retain=True)

        return len(collected_topics)

    def print_devices(self, devices, output_format='table', offline_only=False):
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
            print(json.dumps(devices, indent=2))
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

        print(f"\nTotal: {len(devices)} devices")

    def print_stranded_devices(self, stranded_devices, output_format='table'):
        """Print stranded devices information."""
        if not stranded_devices:
            print("\nNo stranded devices found.")
            return

        total = sum(len(devices) for devices in stranded_devices.values())

        if output_format == 'json':
            print(json.dumps(stranded_devices, indent=2))
            return

        if output_format == 'csv':
            print("\nBridge,Device,Availability")
            for bridge, devices in stranded_devices.items():
                for device_info in devices:
                    print(f"{bridge},{device_info['device']},{device_info['availability']}")
            return

        # Table format
        print(f"\n{'='*60}")
        print("STRANDED DEVICES (retained MQTT messages, not in coordinator)")
        print(f"{'='*60}")
        print(f"\nFound {total} stranded device(s):\n")

        for bridge, devices in stranded_devices.items():
            print(f"{bridge}:")
            for device_info in sorted(devices, key=lambda x: x['device']):
                state = device_info['availability']
                if state:
                    print(f"  - {device_info['device']} (availability: {state})")
                else:
                    print(f"  - {device_info['device']}")

    def send_email_notification(self, offline_devices):
        """Send email notification about offline devices."""
        if not all([config.SMTP_HOST, config.FROM_EMAIL, config.TO_EMAIL]):
            print("Error: Missing email configuration. Check your .env file.", file=sys.stderr)
            return False

        try:
            subject = "Zigbee devices offline"
            body_lines = ["The following Zigbee devices are offline:\n"]

            for device in offline_devices:
                body_lines.append(f"- {device['bridge']} - {device['friendly_name']}")

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
    parser.add_argument("--filter", help="Filter devices by name (case insensitive)")
    parser.add_argument("--offline", "-o", action="store_true",
                        help="Show only offline devices")
    parser.add_argument("--email", "-e", action="store_true",
                        help="Send email notification if offline devices found")
    parser.add_argument("--stranded", "-s", action="store_true",
                        help="Detect stranded devices (retained MQTT messages for removed devices)")
    parser.add_argument("--remove-stranded", action="store_true",
                        help="Remove stranded device retained messages (implies --stranded)")

    args = parser.parse_args()

    # --remove-stranded implies --stranded
    if args.remove_stranded:
        args.stranded = True

    collector = ZigbeeDeviceCollector(default_bridges)

    try:
        if collector.collect_devices(scan_stranded=args.stranded):
            devices = collector.get_merged_devices()

            # Apply name filter if specified
            if args.filter:
                devices = [d for d in devices
                           if args.filter.lower() in d['friendly_name'].lower()]

            # Get offline devices for email
            offline_devices = [d for d in devices if d['availability'] == 'offline']

            # Display device results (unless only showing stranded)
            if not args.stranded or args.offline:
                collector.print_devices(devices, args.format, args.offline)

            # Handle stranded device detection and removal
            if args.stranded:
                stranded = collector.get_stranded_devices()
                collector.print_stranded_devices(stranded, args.format)

                if stranded and args.remove_stranded:
                    print(f"\n{'='*60}")
                    print("REMOVING STRANDED DEVICES")
                    print(f"{'='*60}\n")
                    cleared = collector.remove_stranded_devices(stranded)
                    print(f"\nCleared {cleared} retained message(s)")
                elif stranded and not args.remove_stranded:
                    print("\nUse --remove-stranded to clear these retained messages.")

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
    finally:
        collector.disconnect()


if __name__ == "__main__":
    main()
