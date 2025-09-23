import requests
import argparse
from datetime import datetime, timezone, timedelta
from config import ALERTMANAGER_API_URL, ALERTMANAGER_CREATED_BY


def create_silence(duration_hours=2):
    """Create a maintenance silence for Goepp Alerts."""
    start_time = datetime.now(timezone.utc).isoformat()
    end_time = (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat()
    headers = {"Content-Type": "application/json"}

    data = {
        "matchers": [
            {
                "name": "grafana_folder",
                "value": "Goepp Alerts",
                "isRegex": False,
                "isEqual": True,
            }
        ],
        "startsAt": start_time,
        "endsAt": end_time,
        "createdBy": ALERTMANAGER_CREATED_BY,
        "comment": "Maintenance window",
    }

    try:
        response = requests.post(f"{ALERTMANAGER_API_URL}/silences", headers=headers, json=data)

        if response.status_code == 200:
            silence_id = response.json().get("silenceID")
            print(f"✓ Silence created successfully")
            print(f"  Silence ID: {silence_id}")
            print(f"  Duration: {duration_hours} hours")
            print(f"  Ends at: {end_time}")
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
    """Remove all active AlertManager silences."""
    headers = {"Content-Type": "application/json"}

    try:
        # Get all silences
        response = requests.get(f"{ALERTMANAGER_API_URL}/silences", headers=headers)

        if response.status_code != 200:
            print(f"✗ Failed to get silences: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail}")
            except:
                print(f"  Response: {response.text}")
            return False

        silences = response.json()
        active_silences = [s for s in silences if s["status"]["state"] == "active"]

        if not active_silences:
            print("ℹ No active silences found")
            return True

        print(f"Found {len(active_silences)} active silence(s)")

        removed_count = 0
        failed_count = 0

        # Delete each active silence
        for silence in active_silences:
            silence_id = silence["id"]
            comment = silence.get("comment", "No comment")

            try:
                delete_response = requests.delete(
                    f"{ALERTMANAGER_API_URL}/silence/{silence_id}",
                    headers=headers
                )

                if delete_response.status_code == 200:
                    print(f"✓ Removed silence: {silence_id} ({comment})")
                    removed_count += 1
                else:
                    print(f"✗ Failed to remove silence {silence_id}: HTTP {delete_response.status_code}")
                    failed_count += 1

            except Exception as e:
                print(f"✗ Failed to remove silence {silence_id}: {e}")
                failed_count += 1

        print(f"\nSummary: {removed_count} removed, {failed_count} failed")
        return failed_count == 0

    except Exception as e:
        print(f"✗ Failed to get silences: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlertManager maintenance script")
    parser.add_argument("--mute", action="store_true", help="Create a maintenance silence")
    parser.add_argument("--unmute", action="store_true", help="Remove all active silences")
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
    else:
        print("Usage: python alertmanager-maintenance.py [--mute|--unmute] [--duration HOURS]")
        print("  --mute      Create a maintenance silence (default: 2 hours)")
        print("  --unmute    Remove all active silences")
        print("  --duration  Silence duration in hours (used with --mute)")
        print("\nExamples:")
        print("  python alertmanager-maintenance.py --mute")
        print("  python alertmanager-maintenance.py --mute --duration 4")
        print("  python alertmanager-maintenance.py --unmute")
