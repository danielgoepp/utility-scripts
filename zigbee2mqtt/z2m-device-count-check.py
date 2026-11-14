#!/usr/bin/env python3
"""Compare configured vs. live Zigbee2MQTT device counts and report to Uptime Kuma.

For each bridge, reads two retained MQTT topics published by the running
Zigbee2MQTT instance:

- <bridge>/bridge/info    -> config.devices (devices in configuration.yaml)
- <bridge>/bridge/devices -> devices Zigbee2MQTT actually has loaded

Devices are matched by IEEE address, so the output names exactly which device
is missing from either side. With --push, the result is sent to an Uptime Kuma
Push monitor (one per bridge): status up/down, a summary message, and the live
device count as the "ping" value so Uptime Kuma graphs the count over time.
"""

import argparse
import json
import sys
import time

import paho.mqtt.client as paho
import requests
from paho.mqtt.enums import CallbackAPIVersion

import config


def collect(bridges, timeout):
    """Return {topic: payload} for the bridge/info and bridge/devices topics."""
    wanted = {f"{b}/bridge/{t}" for b in bridges for t in ("info", "devices")}
    messages = {}

    def on_message(client, userdata, message):
        messages[message.topic] = json.loads(message.payload)

    client = paho.Client(client_id="z2m-device-count-check", callback_api_version=CallbackAPIVersion.VERSION2)
    client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
    client.on_message = on_message
    client.connect(config.MQTT_HOST, config.MQTT_PORT)
    client.loop_start()
    client.subscribe([(topic, 0) for topic in wanted])

    deadline = time.time() + timeout
    while time.time() < deadline and not wanted <= messages.keys():
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()
    return messages


def check_bridge(bridge, messages):
    """Return a result dict comparing configured and live devices for one bridge."""
    info = messages.get(f"{bridge}/bridge/info")
    devices = messages.get(f"{bridge}/bridge/devices")
    if info is None or devices is None:
        return {"bridge": bridge, "ok": False, "live": None, "configured": None,
                "message": f"{bridge}: no bridge/info or bridge/devices received (is Zigbee2MQTT running?)"}

    configured = info["config"]["devices"]
    live = {d["ieee_address"]: d.get("friendly_name") for d in devices if d.get("type") != "Coordinator"}

    missing_live = sorted(set(configured) - set(live))
    missing_config = sorted(set(live) - set(configured))

    def describe(ieee, name):
        return f"{name} ({ieee})" if name else ieee

    parts = [f"{bridge}: {len(live)} live / {len(configured)} configured"]
    if missing_live:
        names = ", ".join(describe(i, configured[i].get("friendly_name")) for i in missing_live)
        parts.append(f"configured but not live: {names}")
    if missing_config:
        names = ", ".join(describe(i, live[i]) for i in missing_config)
        parts.append(f"live but not configured: {names}")

    return {"bridge": bridge, "ok": not (missing_live or missing_config),
            "live": len(live), "configured": len(configured), "message": "; ".join(parts)}


def push(result):
    """Send a result to the bridge's Uptime Kuma Push monitor, if one is configured."""
    url = config.uptime_kuma_push_url(result["bridge"])
    if not url:
        print(f"{result['bridge']}: no push URL configured, skipping push", file=sys.stderr)
        return
    params = {"status": "up" if result["ok"] else "down", "msg": result["message"]}
    if result["live"] is not None:
        params["ping"] = result["live"]
    requests.get(url, params=params, timeout=10).raise_for_status()


def main():
    default_bridges = [f"zigbee{i.strip()}" for i in config.Z2M_INSTANCES]

    parser = argparse.ArgumentParser(description="Compare configured vs. live Zigbee2MQTT device counts")
    parser.add_argument("--bridge", "-b", action="append",
                        help=f"Bridge to check (repeatable, default: {', '.join(default_bridges)})")
    parser.add_argument("--push", "-p", action="store_true",
                        help="Report results to the Uptime Kuma Push monitor for each bridge")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    parser.add_argument("--timeout", "-t", type=int, default=config.Z2M_TIMEOUT,
                        help="Seconds to wait for retained MQTT messages")
    args = parser.parse_args()

    bridges = args.bridge or default_bridges
    messages = collect(bridges, args.timeout)
    results = [check_bridge(b, messages) for b in bridges]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"[{'OK' if r['ok'] else 'MISMATCH'}] {r['message']}")

    if args.push:
        for r in results:
            push(r)

    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
