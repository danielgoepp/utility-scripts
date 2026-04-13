#!/usr/bin/env python3
"""Download the most recent Todoist backup.

Requires:
  - TODOIST_OAUTH_TOKEN: saved by setup-oauth.py, used to list available backups
  - TODOIST_API_TOKEN: personal token (Settings > Integrations > Developer),
    used to download the backup file

Usage:
    python3 todoist/download-backup.py
    python3 todoist/download-backup.py --output-dir ~/backups/todoist
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE)

TODOIST_OAUTH_TOKEN = os.getenv("TODOIST_OAUTH_TOKEN")
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
TODOIST_BASE_URL = "https://api.todoist.com/api/v1"
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/Downloads")


def get_latest_backup():
    resp = requests.get(
        f"{TODOIST_BASE_URL}/backups",
        headers={"Authorization": f"Bearer {TODOIST_OAUTH_TOKEN}"},
        timeout=10,
    )
    resp.raise_for_status()
    backups = sorted(resp.json(), key=lambda b: b["version"], reverse=True)
    return backups[0] if backups else None


def download_backup(backup, output_dir):
    version = backup["version"]
    safe_version = version.replace(" ", "_").replace(":", "-")
    filename = f"todoist-backup-{safe_version}.zip"
    dest = os.path.join(output_dir, filename)

    if os.path.exists(dest):
        print(f"Already exists, skipping: {dest}")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"Downloading backup {version!r}...")

    resp = requests.get(
        backup["url"],
        headers={"Authorization": f"Bearer {TODOIST_API_TOKEN}"},
        stream=True,
        timeout=60,
    )
    resp.raise_for_status()

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Saved to: {dest}")


def main():
    parser = argparse.ArgumentParser(description="Download the most recent Todoist backup")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save the backup file (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    if not TODOIST_OAUTH_TOKEN or not TODOIST_API_TOKEN:
        print(
            "Error: TODOIST_OAUTH_TOKEN and TODOIST_API_TOKEN must both be set in .env.\n"
            "Run setup-oauth.py to obtain the OAuth token.",
            file=sys.stderr,
        )
        sys.exit(1)

    backup = get_latest_backup()
    if not backup:
        print("No backups available.")
        sys.exit(0)

    download_backup(backup, args.output_dir)


if __name__ == "__main__":
    main()
