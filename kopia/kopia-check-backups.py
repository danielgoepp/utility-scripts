"""
Check Kopia backup health by verifying all sources have recent snapshots.

Connects to multiple Kopia server instances via the Control API to check
that all configured backup sources are healthy: not paused, not errored,
and have completed a snapshot within the configured maximum age threshold.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import requests
from config import (
    ALERTMANAGER_URL,
    KOPIA_INSTANCES,
    KOPIA_MAX_SNAPSHOT_AGE_HOURS,
    KOPIA_VERIFY_TLS,
    get_instance_config,
)


def get_control_session(instance):
    """Create a requests session with Control API auth for an instance."""
    session = requests.Session()
    session.auth = (instance["control_username"], instance["control_password"])
    session.verify = KOPIA_VERIFY_TLS
    return session


def check_repo_status(session, server_url):
    """Check that the Kopia repository is connected and reachable."""
    resp = session.get(f"{server_url}/api/v1/control/status")
    resp.raise_for_status()
    status = resp.json()
    if not status.get("connected"):
        raise RuntimeError("Repository is not connected")
    return status


def get_sources(session, server_url):
    """Retrieve all configured backup sources with their status."""
    resp = session.get(f"{server_url}/api/v1/control/sources")
    resp.raise_for_status()
    return resp.json().get("sources", [])


def parse_time(time_str):
    """Parse an ISO 8601 timestamp from Kopia."""
    if not time_str:
        return None
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def format_age(hours):
    """Format an age in hours to a human-readable string."""
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 48:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f}d"


def check_sources(sources, max_age_hours):
    """Check all sources for health issues.

    Returns a list of (source_label, status, message) tuples.
    All sources are included regardless of status.
    """
    now = datetime.now(timezone.utc)
    results = []

    for source_info in sources:
        source = source_info.get("source", {})
        label = f"{source.get('userName', '?')}@{source.get('host', '?')}:{source.get('path', '?')}"
        status = source_info.get("status", "UNKNOWN")

        if status == "PAUSED":
            results.append((label, "WARNING", "Source is paused"))
            continue

        last_snapshot = source_info.get("lastSnapshot")
        if not last_snapshot:
            results.append((label, "ERROR", "No snapshots found"))
            continue

        end_time = parse_time(last_snapshot.get("endTime"))
        if not end_time:
            if parse_time(last_snapshot.get("startTime")):
                results.append((label, "WARNING", "Last snapshot has no end time (may be incomplete)"))
            else:
                results.append((label, "ERROR", "Last snapshot has no timestamp"))
            continue

        age_hours = (now - end_time).total_seconds() / 3600
        age_str = format_age(age_hours)
        next_time = parse_time(source_info.get("nextSnapshotTime"))

        if age_hours > max_age_hours:
            results.append((label, "ERROR", f"Last snapshot is {age_str} old (threshold: {max_age_hours}h)"))
        elif next_time and next_time < now:
            overdue_str = format_age((now - next_time).total_seconds() / 3600)
            results.append((label, "WARNING", f"Snapshot overdue by {overdue_str} (last snapshot {age_str} ago)"))
        else:
            next_str = f", next in {format_age((next_time - now).total_seconds() / 3600)}" if next_time else ""
            results.append((label, "OK", f"Last snapshot {age_str} ago{next_str}"))

    return results


def send_alerts(all_results, instance_errors):
    """Send alerts to Alertmanager. Fires for errors/warnings, resolves for healthy sources."""
    now = datetime.now(timezone.utc).isoformat()
    alerts = []

    for instance_name, results in all_results.items():
        for label, status, message in results:
            severity = {"ERROR": "critical", "WARNING": "warning"}.get(status)
            labels = {
                "alertname": "KopiaBackupUnhealthy",
                "instance": instance_name,
                "source": label,
                "severity": severity or "none",
            }
            annotations = {
                "summary": f"Kopia backup issue on {instance_name}: {label}",
                "description": message,
            }
            if severity:
                alerts.append({"labels": labels, "annotations": annotations, "startsAt": now})
            else:
                alerts.append({"labels": labels, "annotations": annotations, "endsAt": now})

    for instance_name, error in instance_errors.items():
        alerts.append({
            "labels": {
                "alertname": "KopiaInstanceUnreachable",
                "instance": instance_name,
                "severity": "critical",
            },
            "annotations": {
                "summary": f"Kopia instance {instance_name} is unreachable",
                "description": error,
            },
            "startsAt": now,
        })

    if not alerts:
        return

    resp = requests.post(f"{ALERTMANAGER_URL}/api/v2/alerts", json=alerts)
    resp.raise_for_status()
    firing = sum(1 for a in alerts if "startsAt" in a)
    resolved = sum(1 for a in alerts if "endsAt" in a)
    print(f"Alertmanager: sent {firing} firing, {resolved} resolved")


def check_instance(instance, max_age_hours):
    """Check a single Kopia instance. Returns (results, source_count)."""
    session = get_control_session(instance)
    server_url = instance["server_url"]
    check_repo_status(session, server_url)
    sources = get_sources(session, server_url)
    return check_sources(sources, max_age_hours), len(sources)


def main():
    parser = argparse.ArgumentParser(
        description="Check Kopia backup health across all configured instances"
    )
    parser.add_argument(
        "--max-age", type=int, default=KOPIA_MAX_SNAPSHOT_AGE_HOURS,
        help=f"Maximum snapshot age in hours (default: {KOPIA_MAX_SNAPSHOT_AGE_HOURS})",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show healthy sources in addition to problems",
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--instance", "-i", action="append",
        help="Check only specific instance(s) (can be repeated)",
    )
    parser.add_argument(
        "--alert", action="store_true",
        help="Send alerts to Alertmanager (requires ALERTMANAGER_URL in .env)",
    )
    args = parser.parse_args()

    if not KOPIA_INSTANCES:
        print("Error: KOPIA_INSTANCES must be set in .env (e.g., KOPIA_INSTANCES=b2,ssd,hdd)")
        sys.exit(2)

    instances_to_check = args.instance or KOPIA_INSTANCES

    # Collect results from all instances
    all_results = {}  # name -> list of (label, status, message)
    instance_urls = {}  # name -> server_url
    instance_errors = {}  # name -> error message
    total_sources = 0

    for name in instances_to_check:
        instance = get_instance_config(name)

        if not instance["server_url"] or not instance["control_password"]:
            instance_errors[name] = f"Missing KOPIA_{name.upper()}_SERVER_URL or KOPIA_{name.upper()}_CONTROL_PASSWORD"
            continue

        instance_urls[name] = instance["server_url"]

        try:
            results, source_count = check_instance(instance, args.max_age)
            all_results[name] = results
            total_sources += source_count
        except (requests.RequestException, RuntimeError) as e:
            instance_errors[name] = str(e)

    # Output results
    if args.output_json:
        output = {
            "instances": [
                {"instance": name, "source": label, "status": status, "message": msg}
                for name, results in all_results.items()
                for label, status, msg in results
            ],
            "errors": [
                {"instance": name, "error": msg}
                for name, msg in instance_errors.items()
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        icons = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌"}

        for name in instances_to_check:
            if name in instance_errors:
                print(f"[{name}] Error: {instance_errors[name]}")
                print()
                continue

            results = all_results[name]
            print(f"[{name}] {instance_urls[name]}")

            problems = [(l, s, m) for l, s, m in results if s != "OK"]
            if not problems and not args.verbose:
                print(f"  All {len(results)} source(s) healthy")
            else:
                shown = results if args.verbose else problems
                for label, status, message in sorted(shown, key=lambda r: {"ERROR": 0, "WARNING": 1, "OK": 2}[r[1]]):
                    print(f"  {icons[status]} {label}: {message}")
            print()

        # Summary
        flat = [r for results in all_results.values() for r in results]
        errors = sum(1 for _, s, _ in flat if s == "ERROR")
        warnings = sum(1 for _, s, _ in flat if s == "WARNING")
        healthy = sum(1 for _, s, _ in flat if s == "OK")
        print(f"Summary: {len(instances_to_check)} instance(s), {total_sources} source(s): "
              f"{healthy} healthy, {warnings} warning(s), {errors} error(s), "
              f"{len(instance_errors)} unreachable")

    # Send alerts to Alertmanager
    if args.alert:
        if not ALERTMANAGER_URL:
            print("Error: ALERTMANAGER_URL must be set in .env to use --alert")
            sys.exit(2)
        try:
            send_alerts(all_results, instance_errors)
        except requests.RequestException as e:
            print(f"Error: Failed to send alerts to Alertmanager: {e}")
            sys.exit(2)

    has_errors = any(s == "ERROR" for results in all_results.values() for _, s, _ in results) or instance_errors
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
