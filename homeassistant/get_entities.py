#!/usr/bin/env python3

import json
import re

entities_registry = open(
    "/Volumes/k3s-prod-data/homeassistant/.storage/core.entity_registry"
)
entities = json.load(entities_registry)

for entity in entities["data"]["entities"]:
    if re.match("automation", entity["entity_id"]):
        # print(json.dumps(entity, indent=2))
        print(f"{entity['entity_id']},{entity['name']},{entity['original_name']}")
