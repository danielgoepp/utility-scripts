#!/usr/bin/env python3
"""
OpenSearch Top Queries Index Purge Script

This script purges old top queries indexes from OpenSearch based on a retention period.
Top queries indexes typically follow a pattern like: top_queries-YYYY.MM.DD
"""

import argparse
import requests
from datetime import datetime, timedelta
import re


OPENSEARCH_URL = "https://opensearch-prod.goepp.net"


def get_indexes(base_url, pattern=None):
    """
    Retrieve all indexes from OpenSearch.

    Args:
        base_url: OpenSearch base URL
        pattern: Optional regex pattern to filter index names

    Returns:
        List of index dictionaries with 'index' and 'creation.date' fields
    """
    url = f"{base_url}/_cat/indices?format=json&h=index,creation.date"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if pattern:
            regex = re.compile(pattern)
            data = [idx for idx in data if regex.match(idx['index'])]

        return data

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving indexes: {e}")
        return []


def parse_date_from_index(index_name, date_pattern=r'(\d{4}\.\d{2}\.\d{2})'):
    """
    Extract date from index name.

    Args:
        index_name: Name of the index (e.g., "top_queries-2024.12.01")
        date_pattern: Regex pattern to match date in index name

    Returns:
        datetime object or None if date cannot be parsed
    """
    match = re.search(date_pattern, index_name)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%Y.%m.%d")
        except ValueError:
            return None
    return None


def delete_index(base_url, index_name, dry_run=False):
    """
    Delete an index from OpenSearch.

    Args:
        base_url: OpenSearch base URL
        index_name: Name of the index to delete
        dry_run: If True, only print what would be deleted without actually deleting

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(f"  [DRY RUN] Would delete: {index_name}")
        return True

    url = f"{base_url}/{index_name}"

    try:
        response = requests.delete(url)
        response.raise_for_status()
        print(f"  ✓ Deleted: {index_name}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error deleting {index_name}: {e}")
        return False


def purge_old_indexes(base_url, index_pattern, retention_days, dry_run=False):
    """
    Purge indexes older than the retention period.

    Args:
        base_url: OpenSearch base URL
        index_pattern: Regex pattern to match index names
        retention_days: Number of days to retain indexes
        dry_run: If True, only print what would be deleted

    Returns:
        Tuple of (deleted_count, total_size_deleted)
    """
    print(f"Retrieving indexes matching pattern: {index_pattern}")
    indexes = get_indexes(base_url, pattern=index_pattern)

    if not indexes:
        print("No matching indexes found.")
        return 0, 0

    print(f"Found {len(indexes)} matching index(es)\n")

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    print(f"Retention policy: {retention_days} days")
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'DELETE'}\n")

    deleted_count = 0
    indexes_to_delete = []
    indexes_to_keep = []

    for index in indexes:
        index_name = index['index']
        index_date = parse_date_from_index(index_name)

        if index_date is None:
            print(f"  ⚠ Warning: Could not parse date from index: {index_name}")
            continue

        if index_date < cutoff_date:
            indexes_to_delete.append((index_name, index_date))
        else:
            indexes_to_keep.append((index_name, index_date))

    # Display summary
    print(f"Indexes to delete: {len(indexes_to_delete)}")
    print(f"Indexes to keep: {len(indexes_to_keep)}\n")

    if indexes_to_delete:
        print("Deleting old indexes:")
        for index_name, index_date in sorted(indexes_to_delete, key=lambda x: x[1]):
            age_days = (datetime.now() - index_date).days
            print(f"  {index_name} (age: {age_days} days, date: {index_date.strftime('%Y-%m-%d')})")
            if delete_index(base_url, index_name, dry_run):
                deleted_count += 1

    print()
    if indexes_to_keep:
        print(f"Keeping {len(indexes_to_keep)} recent indexes:")
        for index_name, index_date in sorted(indexes_to_keep, key=lambda x: x[1], reverse=True)[:5]:
            age_days = (datetime.now() - index_date).days
            print(f"  {index_name} (age: {age_days} days, date: {index_date.strftime('%Y-%m-%d')})")
        if len(indexes_to_keep) > 5:
            print(f"  ... and {len(indexes_to_keep) - 5} more")

    return deleted_count, len(indexes_to_delete)


def main():
    parser = argparse.ArgumentParser(
        description="Purge old top queries indexes from OpenSearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted (30 days retention)
  python3 opensearch-purge-top-queries.py --dry-run

  # Delete indexes older than 30 days (default)
  python3 opensearch-purge-top-queries.py

  # Delete indexes older than 90 days
  python3 opensearch-purge-top-queries.py --retention-days 90

  # Custom index pattern
  python3 opensearch-purge-top-queries.py --pattern "^custom_queries-.*"
        """
    )

    parser.add_argument(
        '--retention-days',
        type=int,
        default=30,
        help='Number of days to retain indexes (default: 30)'
    )

    parser.add_argument(
        '--pattern',
        type=str,
        default=r'^top_queries-.*',
        help='Regex pattern to match index names (default: ^top_queries-.*)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--url',
        type=str,
        default=OPENSEARCH_URL,
        help=f'OpenSearch URL (default: {OPENSEARCH_URL})'
    )

    args = parser.parse_args()

    print(f"OpenSearch URL: {args.url}")
    print("=" * 70)
    print()

    deleted_count, total_count = purge_old_indexes(
        args.url,
        args.pattern,
        args.retention_days,
        args.dry_run
    )

    print()
    print("=" * 70)
    if args.dry_run:
        print(f"Summary: Would delete {deleted_count} of {total_count} old indexes")
        print("\nRun without --dry-run to actually delete these indexes")
    else:
        print(f"Summary: Successfully deleted {deleted_count} of {total_count} old indexes")


if __name__ == "__main__":
    main()
