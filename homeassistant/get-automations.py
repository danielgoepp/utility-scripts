#!/usr/bin/env python3

import sys
import requests
import yaml
import config


def api_session():
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {config.ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
    )
    return session


def get_automation_entities(session):
    response = session.get(f"https://{config.HOST}/api/states")

    if response.status_code != 200:
        print(f"Failed to retrieve states, status code: {response.status_code}")
        print(response.text)
        return None

    return [
        entity
        for entity in response.json()
        if entity["entity_id"].startswith("automation.")
    ]


def get_automation_config(session, automation_id):
    response = session.get(
        f"https://{config.HOST}/api/config/automation/config/{automation_id}"
    )

    if response.status_code != 200:
        print(
            f"Failed to retrieve automation {automation_id}, "
            f"status code: {response.status_code}",
            file=sys.stderr,
        )
        return None

    return response.json()


def main():
    session = api_session()

    entities = get_automation_entities(session)
    if entities is None:
        raise SystemExit(1)

    indexed_automations = {}

    for count, entity in enumerate(entities, 1):
        # Automations created through the UI carry their config id here;
        # YAML-only automations without an id cannot be fetched by config API.
        automation_id = entity["attributes"].get("id")
        if not automation_id:
            print(
                f"Skipping {entity['entity_id']}: no config id",
                file=sys.stderr,
            )
            continue

        # Fetching every config takes a few seconds, so show progress when
        # running interactively without polluting redirected output.
        if sys.stderr.isatty():
            print(f"Fetching {count}/{len(entities)}...", end="\r", file=sys.stderr)

        automation = get_automation_config(session, automation_id)
        if automation is None:
            continue

        alias = automation.get("alias", entity["entity_id"])
        indexed_automations[alias] = automation

    if sys.stderr.isatty():
        print(" " * 40, end="\r", file=sys.stderr)

    print(yaml.dump(indexed_automations))


if __name__ == "__main__":
    main()
