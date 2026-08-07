#!/usr/bin/env python3
"""Find MQTT-discovered entities whose templates reference a missing JSON attribute and request the device report it."""

import argparse
import json
import re
import sys
import time

import paho.mqtt.client as paho

import config

ATTRIBUTE_ERROR_RE = re.compile(r"has no attribute '([^']+)'")
DISCOVERY_TOPICS = ["homeassistant/+/+/config", "homeassistant/+/+/+/config"]


class TemplateAttributeFixer:
    """Scan MQTT discovery configs for templates referencing a given JSON key."""

    def __init__(self):
        self.client = None
        self.configs = []  # list of (topic, payload dict)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            print(f"Failed to connect to MQTT broker: {rc}", file=sys.stderr)
            sys.exit(1)
        client.subscribe([(t, 0) for t in DISCOVERY_TOPICS])

    def on_message(self, client, userdata, message):
        if not message.payload:
            return
        try:
            payload = json.loads(message.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if isinstance(payload, dict):
            self.configs.append((message.topic, payload))

    def collect(self, timeout):
        self.client = paho.Client(
            client_id="z2m-attribute-fixer", callback_api_version=paho.CallbackAPIVersion.VERSION2
        )
        self.client.username_pw_set(username=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(config.MQTT_HOST, config.MQTT_PORT)
        self.client.loop_start()
        print(f"Collecting MQTT discovery configs for {timeout}s...", file=sys.stderr)
        time.sleep(timeout)

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def find_matches(self, key):
        """Return [(device_name, template_field, state_topic), ...] for configs whose
        templates reference value_json["<key>"] or value_json.<key>, deduped by topic."""
        pattern = re.compile(
            r"value_json(?:\[[\"']" + re.escape(key) + r"[\"']\]|\." + re.escape(key) + r"\b)"
        )
        matches = []
        for topic, payload in self.configs:
            for field, value in payload.items():
                if not field.endswith("_template") or not isinstance(value, str):
                    continue
                if not pattern.search(value):
                    continue
                topic_field = field[: -len("_template")] + "_topic"
                state_topic = payload.get(topic_field) or payload.get("state_topic")
                if not state_topic:
                    print(f"  Skipping {field} on {topic}: no matching topic field", file=sys.stderr)
                    continue
                device_name = (payload.get("device") or {}).get("name") or payload.get("object_id") or topic
                matches.append((device_name, field, state_topic))

        seen_topics = set()
        deduped = []
        for device_name, field, state_topic in matches:
            if state_topic in seen_topics:
                continue
            seen_topics.add(state_topic)
            deduped.append((device_name, field, state_topic))
        return deduped

    def request_attribute(self, key, state_topic, dry_run):
        get_topic = f"{state_topic}/get"
        payload = json.dumps({key: ""})
        if dry_run:
            print(f"  [dry-run] Would publish {payload} to {get_topic}")
        else:
            self.client.publish(get_topic, payload)
            print(f"  Published {payload} to {get_topic}")


def extract_keys(text):
    return sorted(set(ATTRIBUTE_ERROR_RE.findall(text)))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find MQTT-discovered entities whose templates reference a missing JSON "
        "attribute (e.g. from a home-assistant.log \"dict object has no attribute 'X'\" "
        "warning) and request the device report it."
    )
    parser.add_argument("--key", help="Attribute key to fix directly (e.g. system_mode)")
    parser.add_argument(
        "--log-line",
        help="Log line(s) containing the warning; the attribute key is extracted "
        "automatically. If omitted and --key is not given, reads from stdin.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=config.Z2M_TIMEOUT,
        help="Seconds to wait for retained discovery messages (default: from config)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be published without publishing"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.key:
        keys = [args.key]
    else:
        text = args.log_line if args.log_line is not None else sys.stdin.read()
        keys = extract_keys(text)
        if not keys:
            print("No \"has no attribute 'X'\" warnings found in input.", file=sys.stderr)
            sys.exit(1)

    fixer = TemplateAttributeFixer()
    try:
        fixer.collect(args.timeout)

        found_any = False
        for key in keys:
            matches = fixer.find_matches(key)
            if not matches:
                print(f"No discovery templates reference '{key}'.")
                continue
            found_any = True
            print(f"\n'{key}' referenced by {len(matches)} device(s):")
            for device_name, field, state_topic in matches:
                print(f"- {device_name} ({field} -> {state_topic})")
                fixer.request_attribute(key, state_topic, args.dry_run)

        if not found_any:
            sys.exit(1)
    finally:
        fixer.disconnect()


if __name__ == "__main__":
    main()
