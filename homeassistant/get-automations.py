#!/usr/bin/env python3

import yaml

with open(
    "/Volumes/k3s-prod-data/homeassistant/automations.yaml"
) as ha_automations_file:
    try:
        automations = yaml.safe_load(ha_automations_file)
    except yaml.YAMLError as exc:
        print(exc)

indexed_automations = {obj["alias"]: obj for obj in automations}

# print(indexed_automations["Lights - Motion - Garage - On"])

print(yaml.dump(indexed_automations))

# if automations:
#     for automation in automations:
#         print(f"{automation['id']} - {automation['alias']}")
