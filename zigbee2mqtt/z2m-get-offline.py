#!/usr/bin/env python3

import json
import sys
import time
import argparse
import smtplib
from email.mime.text import MIMEText
import paho.mqtt.client as paho
import config


class ZigbeeOfflineMonitor:
    """Monitor Zigbee devices for offline status and send email notifications."""

    def __init__(self):
        self.offline_devices = []
        self.scan_complete = False

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT connection."""
        if rc == 0:
            print("Connected to MQTT broker", file=sys.stderr)
        else:
            print(f"Failed to connect to MQTT broker: {rc}", file=sys.stderr)
            sys.exit(1)

    def on_message(self, client, userdata, message):
        """Process MQTT availability messages."""
        try:
            topic_parts = message.topic.split("/")
            if len(topic_parts) >= 2:
                bridge_name = topic_parts[0]  # e.g., 'zigbee11', 'zigbee15'
                device_name = topic_parts[1]

                data = json.loads(message.payload.decode())
                if data.get("state") == "offline":
                    self.offline_devices.append({
                        'bridge': bridge_name,
                        'device': device_name,
                        'status': 'offline'
                    })
                    print(f"Found offline device: {bridge_name} - {device_name}")

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON message: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)

    def scan_for_offline_devices(self, timeout=5):
        """Scan for offline Zigbee devices."""
        if not all([config.MQTT_HOST, config.MQTT_USERNAME, config.MQTT_PASSWORD]):
            print("Error: Missing MQTT configuration. Check your .env file.", file=sys.stderr)
            sys.exit(1)

        client = paho.Client(client_id="z2m-offline-monitor", callback_api_version=paho.CallbackAPIVersion.VERSION2)
        client.username_pw_set(username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        try:
            client.connect(config.MQTT_HOST, config.MQTT_PORT)
            client.loop_start()

            # Subscribe to availability topics for multiple bridges
            availability_topics = [
                ("zigbee11/+/availability", 0),
                ("zigbee15/+/availability", 0)
            ]
            client.subscribe(availability_topics)

            print(f"Scanning for offline devices for {timeout} seconds...", file=sys.stderr)
            time.sleep(timeout)

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

    def send_email_notification(self, offline_devices):
        """Send email notification about offline devices."""
        if not all([config.SMTP_HOST, config.FROM_EMAIL, config.TO_EMAIL]):
            print("Error: Missing email configuration. Check your .env file.", file=sys.stderr)
            return False

        try:
            # Create email content
            subject = "Zigbee devices offline"
            body_lines = ["The following Zigbee devices are offline:\n"]

            for device in offline_devices:
                body_lines.append(f"• {device['bridge']} - {device['device']}: {device['status']}")

            body = "\n".join(body_lines)

            # Create email message
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = config.FROM_EMAIL
            msg['To'] = config.TO_EMAIL

            # Send email
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.send_message(msg)

            print(f"Email notification sent to {config.TO_EMAIL}")
            return True

        except Exception as e:
            print(f"Error sending email notification: {e}", file=sys.stderr)
            return False

    def print_offline_devices(self, output_format='table'):
        """Print offline devices in specified format."""
        if not self.offline_devices:
            print("No offline devices found.")
            return

        if output_format == 'json':
            print(json.dumps(self.offline_devices, indent=2))
            return

        if output_format == 'csv':
            print("Bridge,Device,Status")
            for device in self.offline_devices:
                print(f"{device['bridge']},{device['device']},{device['status']}")
            return

        # Table format
        print(f"\nFound {len(self.offline_devices)} offline devices:")
        print(f"{'Bridge':<15} {'Device':<30} {'Status':<10}")
        print("-" * 55)

        for device in self.offline_devices:
            print(f"{device['bridge']:<15} {device['device']:<30} {device['status']:<10}")


def main():
    """Main function to monitor Zigbee device availability."""
    parser = argparse.ArgumentParser(description="Monitor Zigbee devices for offline status")
    parser.add_argument("--email", "-e", action="store_true",
                       help="Send email notification if offline devices found")
    parser.add_argument("--format", "-f", choices=['table', 'csv', 'json'],
                       default='table', help="Output format")
    parser.add_argument("--timeout", "-t", type=int, default=5,
                       help="Scan timeout in seconds (default: 5)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Only show results, suppress status messages")

    args = parser.parse_args()

    monitor = ZigbeeOfflineMonitor()

    try:
        # Scan for offline devices
        if monitor.scan_for_offline_devices(timeout=args.timeout):
            # Display results
            if not args.quiet:
                monitor.print_offline_devices(args.format)

            # Send email notification if requested and devices found
            if args.email and monitor.offline_devices:
                monitor.send_email_notification(monitor.offline_devices)

            # Exit with error code if offline devices found
            if monitor.offline_devices:
                sys.exit(1)
            else:
                if not args.quiet:
                    print("All devices are online.")

        else:
            print("Failed to scan for offline devices.", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()