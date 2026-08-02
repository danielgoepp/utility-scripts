#!/usr/bin/env python3

import argparse
import requests
import config


def get_states():
    headers = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.get(f"https://{config.HOST}/api/states", headers=headers)

    if response.status_code != 200:
        print(f"Failed to retrieve devices, status code: {response.status_code}")
        print(response.text)
        return None

    return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="List Home Assistant entities and their states"
    )
    parser.add_argument(
        "--unavailable",
        action="store_true",
        help="Only show entities Home Assistant cannot reach (state 'unavailable')",
    )
    parser.add_argument(
        "--unknown",
        action="store_true",
        help="Only show entities with no reported value (state 'unknown')",
    )
    parser.add_argument(
        "--state",
        help="Only show entities matching this exact state (e.g. on, off, home)",
    )
    parser.add_argument(
        "--domain",
        help="Only show entities in this domain (e.g. light, sensor, switch)",
    )
    parser.add_argument(
        "--attributes",
        action="store_true",
        help="Include the full attributes dict in the output",
    )
    args = parser.parse_args()

    devices = get_states()
    if devices is None:
        raise SystemExit(1)

    # --unavailable and --unknown are additive, so passing both shows either.
    wanted_states = set()
    if args.unavailable:
        wanted_states.add("unavailable")
    if args.unknown:
        wanted_states.add("unknown")
    if wanted_states:
        devices = [d for d in devices if d["state"].lower() in wanted_states]

    if args.state:
        devices = [d for d in devices if d["state"].lower() == args.state.lower()]

    if args.domain:
        prefix = f"{args.domain}."
        devices = [d for d in devices if d["entity_id"].startswith(prefix)]

    devices.sort(key=lambda d: d["entity_id"])

    for device in devices:
        name = device["attributes"].get("friendly_name", "")
        line = (
            f"Entity ID: {device['entity_id']}, Name: {name}, State: {device['state']}"
        )
        if args.attributes:
            line += f", Attributes: {device['attributes']}"
        print(line)

    if wanted_states or args.state or args.domain:
        print(f"\nTotal: {len(devices)}")


if __name__ == "__main__":
    main()
