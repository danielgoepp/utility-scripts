#!/usr/bin/env python3

import argparse
import json
import smtplib
import subprocess
import sys
from email.mime.text import MIMEText
from pathlib import Path

import config

DEFAULT_SCAN_ROOT = Path.home() / "Development"
DEFAULT_SYSTEM_PYTHON = "/opt/homebrew/bin/python3"
VENV_DIRNAMES = (".venv", "venv")
SKIP_DIRNAMES = {".git", "__pycache__", "node_modules", ".venv", "venv"}
MAX_SCAN_DEPTH = 3


def find_venv_pythons(scan_root, max_depth=MAX_SCAN_DEPTH):
    """Find venv python executables under scan_root, one entry per project."""
    targets = []

    def walk(directory, depth):
        if depth > max_depth:
            return
        try:
            children = sorted(p for p in directory.iterdir() if p.is_dir())
        except PermissionError:
            return

        for child in children:
            if child.name in VENV_DIRNAMES:
                python_binary = child / "bin" / "python3"
                if python_binary.exists():
                    targets.append((directory.name, python_binary))
                continue
            if child.name in SKIP_DIRNAMES or child.name.startswith("."):
                continue
            walk(child, depth + 1)

    walk(scan_root, 0)
    return targets


def get_outdated_packages(python_binary):
    """Return a list of {name, version, latest_version} dicts for outdated packages."""
    result = subprocess.run(
        [str(python_binary), "-m", "pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"    Failed to check outdated packages: {result.stderr.strip()}", file=sys.stderr)
        return []
    return json.loads(result.stdout)


def upgrade_package(python_binary, name, break_system_packages, dry_run):
    if dry_run:
        return "upgraded", ""

    cmd = [str(python_binary), "-m", "pip", "install", "--upgrade"]
    if break_system_packages:
        cmd.append("--break-system-packages")
    cmd.append(name)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return "upgraded", ""
    if "uninstall-no-record-file" in result.stderr:
        return "skipped", "installed by brew; run 'brew upgrade' to update it"
    return "failed", result.stderr.strip()


def process_target(label, python_binary, break_system_packages, dry_run):
    print(f"\n{label} ({python_binary})")

    outdated = get_outdated_packages(python_binary)
    if not outdated:
        print("  Up to date")
        return []

    results = []
    for pkg in outdated:
        name, current, latest = pkg["name"], pkg["version"], pkg["latest_version"]
        action = "Would upgrade" if dry_run else "Upgrading"
        print(f"  {action} {name}: {current} -> {latest}")

        status, message = upgrade_package(python_binary, name, break_system_packages, dry_run)
        if status == "skipped":
            print(f"    Skipped: {message}")
        elif status == "failed":
            print(f"    Failed: {message}", file=sys.stderr)

        results.append({"name": name, "current": current, "latest": latest, "status": status, "message": message})

    return results


def build_report(target_results, dry_run):
    """Build a plain-text report from {label: [package results]} and return (subject, body, had_failures)."""
    upgraded = sum(1 for results in target_results.values() for r in results if r["status"] == "upgraded")
    skipped = sum(1 for results in target_results.values() for r in results if r["status"] == "skipped")
    failed = sum(1 for results in target_results.values() for r in results if r["status"] == "failed")

    verb = "would be upgraded" if dry_run else "upgraded"
    summary = f"{upgraded} {verb}, {skipped} skipped, {failed} failed"
    prefix = "[DRY RUN] " if dry_run else ""
    subject = f"{prefix}Python Maintenance: {summary}" if (upgraded or skipped or failed) else f"{prefix}Python Maintenance: all up to date"

    lines = [f"Summary: {summary}", ""]
    for label, results in target_results.items():
        lines.append(label)
        if not results:
            lines.append("  Up to date")
        for r in results:
            action = "Would upgrade" if dry_run else {"upgraded": "Upgraded", "skipped": "Skipped", "failed": "FAILED"}[r["status"]]
            lines.append(f"  {action} {r['name']}: {r['current']} -> {r['latest']}")
            if r["message"]:
                lines.append(f"    {r['message']}")
        lines.append("")

    return subject, "\n".join(lines), failed > 0


def send_email(subject, body):
    if not all([config.SMTP_HOST, config.FROM_EMAIL, config.TO_EMAIL]):
        print("Error: Missing email configuration. Check your .env file.", file=sys.stderr)
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.FROM_EMAIL
        msg["To"] = config.TO_EMAIL

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.send_message(msg)

        print(f"Email notification sent to {config.TO_EMAIL}")
        return True
    except Exception as e:
        print(f"Error sending email notification: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Upgrade outdated Python packages across project venvs and the Homebrew system Python."
    )
    parser.add_argument(
        "--scan-root",
        type=Path,
        default=DEFAULT_SCAN_ROOT,
        help=f"Directory to search for project venvs (default: {DEFAULT_SCAN_ROOT})",
    )
    parser.add_argument(
        "--system-python",
        default=DEFAULT_SYSTEM_PYTHON,
        help=f"Path to the system/Homebrew Python executable (default: {DEFAULT_SYSTEM_PYTHON})",
    )
    parser.add_argument("--system-only", action="store_true", help="Only upgrade the system Python packages")
    parser.add_argument("--venvs-only", action="store_true", help="Only upgrade project venvs, skip system Python")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List outdated packages without upgrading anything",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Email a summary of the run to TO_EMAIL (requires SMTP settings in .env)",
    )
    args = parser.parse_args()

    if args.system_only and args.venvs_only:
        parser.error("--system-only and --venvs-only are mutually exclusive")

    targets = []
    if not args.venvs_only:
        system_python = Path(args.system_python)
        if system_python.exists():
            targets.append(("System (Homebrew Python)", system_python, True))
        else:
            print(f"System Python not found at {system_python}, skipping", file=sys.stderr)

    if not args.system_only:
        for project_name, python_binary in find_venv_pythons(args.scan_root):
            targets.append((f"venv: {project_name}", python_binary, False))

    if not targets:
        print("No targets found")
        return

    target_results = {}
    for label, python_binary, break_system_packages in targets:
        target_results[label] = process_target(label, python_binary, break_system_packages, args.dry_run)

    subject, body, had_failures = build_report(target_results, args.dry_run)
    print(f"\n{subject}")

    if args.email:
        send_email(subject, body)

    if had_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
