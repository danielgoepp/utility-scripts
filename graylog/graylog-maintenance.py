import argparse
import requests
import os
from requests.auth import HTTPBasicAuth
from config import GRAYLOG_API_URL, GRAYLOG_USERNAME, GRAYLOG_PASSWORD


def mute_events():
    """Mute all Graylog event definitions except system notifications."""
    url = f"{GRAYLOG_API_URL}/events/definitions"
    headers = {"X-Requested-By": "python-script"}
    auth = HTTPBasicAuth(GRAYLOG_USERNAME, GRAYLOG_PASSWORD)

    try:
        response = requests.get(url, auth=auth)
        if response.status_code != 200:
            print(f"✗ Failed to get event definitions: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail}")
            except:
                print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Failed to get events: {e}")
        return False

    event_definitions = response.json().get("event_definitions", [])
    if not event_definitions:
        print("ℹ No event definitions found")
        return True

    muted_count = 0
    skipped_count = 0
    failed_count = 0

    print(f"Processing {len(event_definitions)} event definitions...")

    # Track events that were already disabled
    try:
        with open("last_disabled.txt", "w") as f:
            for event in event_definitions:
                event_id = event["id"]
                title = event["title"]
                state = event["state"]

                if state == "DISABLED":
                    f.write(f"{event_id}\n")
                    print(f"ℹ Already disabled: {title}")
                    skipped_count += 1
                    continue

                if event.get("_scope") == "SYSTEM_NOTIFICATION_EVENT":
                    print(f"ℹ Skipping system event: {title}")
                    skipped_count += 1
                    continue

                try:
                    mute_response = requests.put(
                        f"{GRAYLOG_API_URL}/events/definitions/{event_id}/unschedule",
                        auth=auth,
                        headers=headers,
                    )
                    if mute_response.status_code == 200:
                        print(f"✓ Muted: {title}")
                        muted_count += 1
                    else:
                        print(f"✗ Failed to mute {title}: HTTP {mute_response.status_code}")
                        failed_count += 1
                except Exception as e:
                    print(f"✗ Failed to mute event {title}: {e}")
                    failed_count += 1

    except Exception as e:
        print(f"✗ Failed to write state file: {e}")
        return False

    print(f"\n✓ Summary: {muted_count} muted, {skipped_count} skipped, {failed_count} failed")
    return failed_count == 0


def unmute_events():
    """Unmute all Graylog event definitions that were not previously disabled."""
    url = f"{GRAYLOG_API_URL}/events/definitions"
    headers = {"X-Requested-By": "python-script"}
    auth = HTTPBasicAuth(GRAYLOG_USERNAME, GRAYLOG_PASSWORD)

    # Read previously disabled events
    try:
        with open("last_disabled.txt", "r") as f:
            last_disabled = f.read().splitlines()
        print(f"ℹ Found {len(last_disabled)} previously disabled events to preserve")
    except FileNotFoundError:
        print("✗ Error: last_disabled.txt not found - cannot safely unmute without knowing which events were previously disabled")
        return False

    try:
        response = requests.get(url, auth=auth)
        if response.status_code != 200:
            print(f"✗ Failed to get event definitions: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail}")
            except:
                print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Failed to get events: {e}")
        return False

    event_definitions = response.json().get("event_definitions", [])
    if not event_definitions:
        print("ℹ No event definitions found")
        return True

    unmuted_count = 0
    skipped_count = 0
    failed_count = 0

    print(f"Processing {len(event_definitions)} event definitions...")

    for event in event_definitions:
        event_id = event["id"]
        title = event["title"]

        if event_id in last_disabled:
            print(f"ℹ Keeping disabled (was already disabled): {title}")
            skipped_count += 1
            continue

        if event.get("_scope") == "SYSTEM_NOTIFICATION_EVENT":
            print(f"ℹ Skipping system event: {title}")
            skipped_count += 1
            continue

        try:
            unmute_response = requests.put(
                f"{GRAYLOG_API_URL}/events/definitions/{event_id}/schedule",
                auth=auth,
                headers=headers,
            )
            if unmute_response.status_code == 200:
                print(f"✓ Unmuted: {title}")
                unmuted_count += 1
            else:
                print(f"✗ Failed to unmute {title}: HTTP {unmute_response.status_code}")
                failed_count += 1
        except Exception as e:
            print(f"✗ Failed to unmute event {title}: {e}")
            failed_count += 1

    print(f"\n✓ Summary: {unmuted_count} unmuted, {skipped_count} skipped, {failed_count} failed")

    # Clean up state file
    try:
        os.remove("last_disabled.txt")
        print("✓ Cleanup: Removed last_disabled.txt")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"⚠ Warning: Could not remove last_disabled.txt: {e}")

    return failed_count == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graylog alert maintenance script")
    parser.add_argument("--mute", action="store_true", help="Mute all event definitions")
    parser.add_argument("--unmute", action="store_true", help="Unmute all event definitions")

    args = parser.parse_args()

    if args.mute and args.unmute:
        print("Error: Cannot use both --mute and --unmute at the same time")
        exit(1)
    elif args.mute:
        success = mute_events()
        exit(0 if success else 1)
    elif args.unmute:
        success = unmute_events()
        exit(0 if success else 1)
    else:
        print("Usage: python graylog-maintenance.py [--mute|--unmute]")
        print("  --mute    Mute all Graylog event definitions")
        print("  --unmute  Unmute all event definitions (except those previously disabled)")
        print("\nExamples:")
        print("  python graylog-maintenance.py --mute")
        print("  python graylog-maintenance.py --unmute")
