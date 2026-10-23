#!/usr/bin/env python3
"""Update an Obsidian note with the applications installed on this Mac.

Collects apps from /Applications and ~/Applications (marking App Store and
Homebrew-managed ones), Homebrew casks and formulae installed on request, and
launchd agents and daemons that run on a schedule, at login/boot, or stay running.

Only two marked regions of the note are touched; everything else is preserved:

- The installed region is regenerated on every run.
- The previously installed region is a list that is only added to: anything
  listed in the installed region on the last run but missing now is appended
  with the date it was last seen. Entries that are installed again are removed.
  Other lines in this region (including hand-written entries) are kept.

If a region's markers are missing, the region is appended to the end of the note.
"""

import argparse
import json
import plistlib
import re
import shutil
import socket
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import config

APP_DIRS = [Path("/Applications"), Path.home() / "Applications"]
LAUNCHD_DIRS = [Path.home() / "Library/LaunchAgents", Path("/Library/LaunchAgents"), Path("/Library/LaunchDaemons")]
WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

INSTALLED_START = "<!-- installed-apps:start -->"
INSTALLED_END = "<!-- installed-apps:end -->"
PREVIOUS_START = "<!-- previously-installed:start -->"
PREVIOUS_END = "<!-- previously-installed:end -->"

# Section headings in the installed region, mapped to the kind of item they list
SECTION_KINDS = {
    "Applications": "app",
    "Homebrew Casks": "cask",
    "Homebrew Formulae": "formula",
    "Scheduled Jobs": "job",
}

# "- Name (kind) — last seen 2026-10-23"; kind and the trailing note are optional
PREVIOUS_ENTRY = re.compile(r"^- (?P<name>.+?)(?: \((?P<kind>app|cask|formula|job)\))?(?: — .*)?$")


def read_app_info(app_path):
    """Return (bundle_id, version) from an app bundle's Info.plist."""
    try:
        with open(app_path / "Contents" / "Info.plist", "rb") as f:
            info = plistlib.load(f)
    except (OSError, plistlib.InvalidFileException):
        return None, None
    version = info.get("CFBundleShortVersionString") or info.get("CFBundleVersion")
    return info.get("CFBundleIdentifier"), version


def find_app_bundles(directory):
    """Yield .app bundles in directory and one folder level below it."""
    if not directory.is_dir():
        return
    for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if child.suffix == ".app":
            yield child
        elif child.is_dir() and not child.name.startswith("."):
            for grandchild in sorted(child.iterdir(), key=lambda p: p.name.lower()):
                if grandchild.suffix == ".app":
                    yield grandchild


def run_brew(args):
    """Run a brew command and return parsed JSON, or None if brew is unavailable."""
    if not shutil.which("brew"):
        return None
    result = subprocess.run(["brew", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"brew {' '.join(args)} failed: {result.stderr.strip()}", file=sys.stderr)
        return None
    return json.loads(result.stdout)


def get_brew_data():
    """Return (casks, formulae, cask_app_names) from Homebrew, or None if brew failed."""
    casks_json = run_brew(["info", "--cask", "--json=v2", "--installed"])
    formulae_json = run_brew(["info", "--json=v2", "--installed"])
    if casks_json is None or formulae_json is None:
        return None

    casks = []
    cask_app_names = {}
    for cask in casks_json["casks"]:
        casks.append((cask["token"], cask.get("installed") or ""))
        for artifact in cask.get("artifacts", []):
            for app_name in artifact.get("app", []):
                if isinstance(app_name, str):
                    cask_app_names[app_name] = cask["token"]

    formulae = []
    for formula in formulae_json["formulae"]:
        installed = formula.get("installed") or []
        if installed and installed[0].get("installed_on_request"):
            formulae.append((formula["name"], installed[0].get("version", "")))

    return sorted(casks), sorted(formulae), cask_app_names


def collect_apps(cask_app_names, include_apple):
    apps = []
    for directory in APP_DIRS:
        for app_path in find_app_bundles(directory):
            bundle_id, version = read_app_info(app_path)
            from_app_store = (app_path / "Contents" / "_MASReceipt").exists()
            # Apple's bundled apps (Safari, Utilities) are part of macOS, not installs
            if not include_apple and not from_app_store and (bundle_id or "").startswith("com.apple."):
                continue

            if from_app_store:
                source = "App Store"
            elif app_path.name in cask_app_names:
                source = f"Homebrew (`{cask_app_names[app_path.name]}`)"
            else:
                source = "Manual"

            location = str(app_path.parent).replace(str(Path.home()), "~")
            apps.append((app_path.stem, version or "", source, location))
    return sorted(apps, key=lambda app: app[0].lower())


def describe_interval(seconds):
    for unit, size in (("d", 86400), ("h", 3600), ("min", 60)):
        if seconds >= size and seconds % size == 0:
            return f"Every {seconds // size}{unit}"
    return f"Every {seconds}s"


def describe_calendar(entries):
    """Describe StartCalendarInterval entries, e.g. "Daily 09:00, 13:00" or "Sun 03:00"."""
    if isinstance(entries, dict):
        entries = [entries]
    times = []
    for entry in entries:
        hour, minute = entry.get("Hour"), entry.get("Minute", 0)
        clock = f"{hour:02d}:{minute:02d}" if hour is not None else f"hourly at :{minute:02d}"
        prefix = []
        if "Month" in entry:
            prefix.append(f"month {entry['Month']}")
        if "Day" in entry:
            prefix.append(f"day {entry['Day']}")
        if "Weekday" in entry:
            prefix.append(WEEKDAYS[entry["Weekday"]])
        times.append((" ".join(prefix), clock))

    if all(not prefix for prefix, _ in times):
        return "Daily " + ", ".join(clock for _, clock in times)
    return ", ".join(f"{prefix} {clock}".strip() for prefix, clock in times)


def describe_schedule(job, is_daemon):
    """Return a schedule description, or None for jobs that only start on demand."""
    parts = []
    if "StartCalendarInterval" in job:
        parts.append(describe_calendar(job["StartCalendarInterval"]))
    if "StartInterval" in job:
        parts.append(describe_interval(job["StartInterval"]))
    if job.get("RunAtLoad"):
        parts.append("At boot" if is_daemon else "At login")
    if job.get("KeepAlive"):
        parts.append("Kept running")
    if job.get("WatchPaths") or job.get("QueueDirectories"):
        parts.append("On file change")
    if not parts:
        return None
    return "; ".join(parts) + (" (disabled)" if job.get("Disabled") else "")


def collect_jobs(include_apple):
    """Return (label, schedule, command, location) for launchd jobs that run on a schedule."""
    jobs = []
    home = str(Path.home())
    for directory in LAUNCHD_DIRS:
        if not directory.is_dir():
            continue
        location = str(directory).replace(home, "~")
        for plist_path in sorted(directory.glob("*.plist")):
            try:
                with open(plist_path, "rb") as f:
                    job = plistlib.load(f)
            except PermissionError:
                jobs.append((plist_path.stem, "Unknown (needs admin to read)", "", location))
                continue
            except (OSError, plistlib.InvalidFileException):
                continue

            label = job.get("Label", plist_path.stem)
            if not include_apple and label.startswith("com.apple."):
                continue
            schedule = describe_schedule(job, directory.name == "LaunchDaemons")
            if schedule is None:
                continue
            command = " ".join(map(str, job.get("ProgramArguments") or [job.get("Program", "")]))
            jobs.append((label, schedule, f"`{command.replace(home, '~')}`" if command else "", location))
    return sorted(jobs, key=lambda job: job[0].lower())


def escape_cell(value):
    return value.replace("|", "\\|")


def render_table(headers, rows):
    """Render a Markdown table with columns padded to equal width, as Obsidian formats them."""
    rows = [[escape_cell(cell) for cell in row] for row in rows]
    widths = [max(len(cell) for cell in column) for column in zip(headers, *rows)]

    def render_row(cells):
        return "| " + " | ".join(cell.ljust(width) for cell, width in zip(cells, widths)) + " |"

    return [render_row(headers), render_row(["-" * width for width in widths]), *map(render_row, rows)]


def render_installed(apps, casks, formulae, jobs):
    lines = [
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} on {socket.gethostname()} by update-installed-apps-note.py._",
        "",
        f"## Applications ({len(apps)})",
        "",
        *render_table(["Application", "Version", "Source", "Location"], apps),
    ]

    if casks:
        lines += ["", f"## Homebrew Casks ({len(casks)})", "", *render_table(["Cask", "Version"], casks)]

    if formulae:
        lines += ["", f"## Homebrew Formulae ({len(formulae)})", "", *render_table(["Formula", "Version"], formulae)]

    if jobs:
        lines += [
            "",
            f"## Scheduled Jobs ({len(jobs)})",
            "",
            *render_table(["Job", "Schedule", "Command", "Location"], jobs),
        ]

    return "\n".join(lines)


def get_region(text, start, end):
    """Return the content between start and end markers, or None if they are missing."""
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start)) if start_index != -1 else -1
    if start_index == -1 or end_index == -1:
        return None
    return text[start_index + len(start) : end_index].strip("\n")


def set_region(text, start, end, content, heading):
    """Replace the content between start and end markers, appending the region if missing."""
    block = f"{start}\n{content}\n{end}" if content else f"{start}\n{end}"
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start)) if start_index != -1 else -1
    if start_index == -1 or end_index == -1:
        return f"{text.rstrip()}\n\n{heading}\n\n{block}\n".lstrip()
    return text[:start_index] + block + text[end_index + len(end) :]


def parse_installed(region):
    """Return the set of (kind, name) items listed in a previously generated installed region."""
    items = set()
    kind = None
    for line in region.splitlines():
        if line.startswith("#"):
            title = re.sub(r" \(\d+\)$", "", line.lstrip("#").strip())
            kind = SECTION_KINDS.get(title)
            continue
        if not kind or not line.startswith("| ") or line.startswith("| ---"):
            continue
        cell = re.split(r"(?<!\\)\|", line)[1].strip().replace("\\|", "|")
        if cell not in ("Application", "Cask", "Formula", "Job"):
            items.add((kind, cell))
    return items


def update_previous(region, removed, current, today):
    """Add removed items to the previously installed list and drop ones installed again."""
    current_names = {name.lower() for _, name in current}
    kept = []
    listed = set()
    for line in (region or "").splitlines():
        match = PREVIOUS_ENTRY.match(line)
        if match:
            name, kind = match["name"], match["kind"]
            if (kind, name) in current or (kind is None and name.lower() in current_names):
                continue
            listed.add(name.lower())
        kept.append(line)

    for kind, name in sorted(removed, key=lambda item: item[1].lower()):
        if name.lower() not in listed:
            kept.append(f"- {name} ({kind}) — last seen {today}")
    return "\n".join(kept).strip("\n")


def main():
    parser = argparse.ArgumentParser(description="Update an Obsidian note with the applications installed on this Mac")
    parser.add_argument("--note", help="Path to the note (default: INSTALLED_APPS_NOTE from .env)")
    parser.add_argument("--include-apple", action="store_true", help="Include Apple's bundled apps and launchd jobs")
    parser.add_argument("--dry-run", action="store_true", help="Print the updated note to stdout instead of writing it")
    args = parser.parse_args()

    note_path = args.note or config.INSTALLED_APPS_NOTE
    if not note_path:
        parser.error("no note path: pass --note or set INSTALLED_APPS_NOTE in .env")
    note = Path(note_path).expanduser()
    text = note.read_text() if note.exists() else ""

    brew_data = get_brew_data()
    if brew_data is None:
        # Writing without Homebrew data would record every cask and formula as removed
        sys.exit("Could not read Homebrew data; note not updated")
    casks, formulae, cask_app_names = brew_data
    apps = collect_apps(cask_app_names, args.include_apple)
    jobs = collect_jobs(args.include_apple)

    current = (
        {("app", name) for name, *_ in apps}
        | {("cask", token) for token, _ in casks}
        | {("formula", name) for name, _ in formulae}
        | {("job", label) for label, *_ in jobs}
    )
    previously_listed = parse_installed(get_region(text, INSTALLED_START, INSTALLED_END) or "")
    removed = previously_listed - current

    previous = update_previous(get_region(text, PREVIOUS_START, PREVIOUS_END), removed, current, date.today())
    text = set_region(text, INSTALLED_START, INSTALLED_END, render_installed(apps, casks, formulae, jobs), "# Installed")
    text = set_region(text, PREVIOUS_START, PREVIOUS_END, previous, "# Previously Installed")

    if args.dry_run:
        print(text, end="")
        return

    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(text)
    print(f"Wrote {len(apps)} apps, {len(casks)} casks, {len(formulae)} formulae, {len(jobs)} jobs to {note}")
    for kind, name in sorted(removed, key=lambda item: item[1].lower()):
        print(f"  No longer installed: {name} ({kind})")


if __name__ == "__main__":
    main()
