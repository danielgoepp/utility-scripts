#!/usr/bin/env python3
"""
OpenSearch Index Field Count Script

This script retrieves all indexes from OpenSearch and displays the number of fields in each one.
"""

import requests

OPENSEARCH_URL = "https://opensearch-prod.goepp.net"


def get_indexes(base_url):
    url = f"{base_url}/_cat/indices?format=json"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        indexes = [index["index"] for index in data]

        return sorted(indexes)

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving indexes: {e}")
        return []


def get_field_count(base_url, index_name):
    url = f"{base_url}/{index_name}/_field_caps?fields=*"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if "fields" in data:
            return len(data["fields"])
        else:
            return 0

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving field count for {index_name}: {e}")
        return None


if __name__ == "__main__":
    print(f"Retrieving indexes from {OPENSEARCH_URL}...")
    indexes = get_indexes(OPENSEARCH_URL)

    if not indexes:
        print("No indexes found.")
        exit(0)

    print(f"Found {len(indexes)} index(es)\n")

    results = []
    for index in indexes:
        field_count = get_field_count(OPENSEARCH_URL, index)
        if field_count is not None:
            results.append((index, field_count))

    # Display results
    print(f"{'Index':<50} {'Field Count':>12}")
    print("-" * 63)

    for index, count in results:
        print(f"{index:<50} {count:>12}")

    # Summary
    if results:
        total_fields = sum(count for _, count in results)
        print("-" * 63)
        print(f"{'Total:':<50} {total_fields:>12}")
