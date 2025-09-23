#!/usr/bin/env python3

import requests
import argparse
import time
from datetime import datetime, timedelta
from config import HERTZBEAT_URL, HERTZBEAT_TOKEN


def create_silence(duration_hours=2):
    """Create an alert silence for the specified duration in hours."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {HERTZBEAT_TOKEN}",
    }

    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)

    # Format as ZonedDateTime with timezone offset like: 2025-09-01T05:50:50.283-04:00
    tz_offset = time.strftime('%z')
    if len(tz_offset) == 5:  # -0400 -> -04:00
        tz_offset = tz_offset[:3] + ':' + tz_offset[3:]

    start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + tz_offset
    end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + tz_offset

    silence_data = {
        "type": 0,  # One-time silence (0 for period-based)
        "name": f"Maintenance Window - {start_time.strftime('%Y-%m-%d %H:%M')}",
        "enable": True,
        "periodStart": start_iso,
        "periodEnd": end_iso,
        "matchAll": True
    }

    try:
        response = requests.post(
            f"{HERTZBEAT_URL}/api/alert/silence",
            headers=headers,
            json=silence_data,
        )

        if response.status_code in [200, 201]:
            try:
                response_data = response.json()
                # Check if the API returned success
                if response_data and response_data.get("code") == 0:
                    print(f"✓ Alert silence created successfully")
                    print(f"  Duration: {duration_hours} hours")
                    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    if response_data.get("msg"):
                        print(f"  Message: {response_data['msg']}")
                    return True
                else:
                    print(f"✗ API returned error: {response_data}")
                    return False
            except Exception as e:
                print(f"✓ Silence created but failed to parse response: {e}")
                return True
        else:
            print(f"✗ Failed to create silence: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail}")
            except:
                print(f"  Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Failed to create silence: {e}")
        return False


def remove_all_silences():
    """Remove all active alert silences."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {HERTZBEAT_TOKEN}",
    }

    try:
        # Get all silences
        response = requests.get(f"{HERTZBEAT_URL}/api/alert/silences", headers=headers)

        if response.status_code != 200:
            print(f"✗ Failed to get silences: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail}")
            except:
                print(f"  Response: {response.text}")
            return False

        data = response.json()
        silences = []

        if data.get("data") and data["data"].get("content"):
            silences = data["data"]["content"]

        if not silences:
            print("ℹ No active silences found")
            return True

        print(f"Found {len(silences)} silence(s)")

        removed_count = 0
        failed_count = 0

        # Delete each silence
        for silence in silences:
            silence_id = silence["id"]
            name = silence.get("name", "Unknown")

            try:
                # Delete the silence using the correct batch endpoint
                delete_response = requests.delete(
                    f"{HERTZBEAT_URL}/api/alert/silences",
                    headers=headers,
                    params={"ids": [silence_id]}
                )

                if delete_response.status_code == 200:
                    response_data = delete_response.json()
                    if response_data and response_data.get("code") == 0:
                        print(f"✓ Deleted silence: {name} (ID: {silence_id})")
                        removed_count += 1
                    else:
                        print(f"✗ Failed to delete silence {silence_id}: {response_data}")
                        failed_count += 1
                else:
                    print(f"✗ Failed to delete silence {silence_id}: HTTP {delete_response.status_code}")
                    failed_count += 1

            except Exception as e:
                print(f"✗ Failed to remove silence {silence_id}: {e}")
                failed_count += 1

        print(f"\n✓ Summary: {removed_count} removed, {failed_count} failed")
        return failed_count == 0

    except Exception as e:
        print(f"✗ Failed to get silences: {e}")
        return False


def list_silences():
    """List all alert silences."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {HERTZBEAT_TOKEN}",
    }

    try:
        response = requests.get(f"{HERTZBEAT_URL}/api/alert/silences", headers=headers)

        if response.status_code != 200:
            print(f"✗ Failed to get silences: HTTP {response.status_code}")
            return False

        data = response.json()

        if data.get("data") and data["data"].get("content"):
            silences = data["data"]["content"]
            print(f"ℹ Found {len(silences)} silence(s):")
            for silence in silences:
                status = "enabled" if silence.get("enable") else "disabled"
                print(f"  ID {silence['id']}: {silence['name']} ({status})")
                if silence.get('type') == 0:  # Period-based
                    print(f"    Period: {silence.get('periodStart')} to {silence.get('periodEnd')}")
        else:
            print("ℹ No silences found")

        return True
    except Exception as e:
        print(f"✗ Failed to get silences: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HertzBeat alert maintenance script")
    parser.add_argument("--mute", action="store_true", help="Create a maintenance silence")
    parser.add_argument("--unmute", action="store_true", help="Remove all active silences")
    parser.add_argument("--list", action="store_true", help="List all silences")
    parser.add_argument("--duration", type=int, default=2, help="Silence duration in hours (default: 2)")

    args = parser.parse_args()

    if args.mute and args.unmute:
        print("Error: Cannot use both --mute and --unmute at the same time")
        exit(1)
    elif args.mute:
        success = create_silence(args.duration)
        exit(0 if success else 1)
    elif args.unmute:
        success = remove_all_silences()
        exit(0 if success else 1)
    elif args.list:
        success = list_silences()
        exit(0 if success else 1)
    else:
        print("Usage: python hertzbeat-maintenance.py [--mute|--unmute|--list] [--duration HOURS]")
        print("  --mute      Create a maintenance silence (default: 2 hours)")
        print("  --unmute    Remove all active silences")
        print("  --list      List all silences")
        print("  --duration  Silence duration in hours (used with --mute)")
        print("\nExamples:")
        print("  python hertzbeat-maintenance.py --mute")
        print("  python hertzbeat-maintenance.py --mute --duration 4")
        print("  python hertzbeat-maintenance.py --unmute")
        print("  python hertzbeat-maintenance.py --list")
