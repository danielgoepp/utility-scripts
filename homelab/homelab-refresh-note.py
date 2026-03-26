"""
Refresh the Home Lab markdown note with live data from the lab infrastructure.

Data sources:
- kubectl: k3s prod cluster node versions, OS, and runtime
- SSH to pve15: ZFS pool usage (SSDPool, HDDPool, rpool)

Updates sections in the note delimited by HTML comment markers:
  <!-- BEGIN:SECTION_NAME --> ... <!-- END:SECTION_NAME -->

Sections updated:
  LAST_REFRESHED   - timestamp of last refresh
  K3S_NODES        - prod cluster node table (IP, OS, runtime, version)
  ZFS_STORAGE      - ZFS pool sizes, free space, and configuration on pve15

Usage:
  python3 homelab/homelab-refresh-note.py
  python3 homelab/homelab-refresh-note.py --dry-run
  python3 homelab/homelab-refresh-note.py --section k3s-nodes
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime

from config import (
    K3S_CONTEXT,
    NOTE_PATH,
    PVE_SSH_USER,
    PVE_STORAGE_HOST,
    SSH_KEY_PATH,
    SSH_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Marker helpers
# ---------------------------------------------------------------------------

MARKER_RE = re.compile(
    r"(<!-- BEGIN:(?P<name>\w+) -->).*?(<!-- END:(?P=name) -->)",
    re.DOTALL,
)


def replace_section(content: str, name: str, new_body: str) -> str:
    """Replace the content between BEGIN/END markers for a named section."""
    pattern = re.compile(
        rf"(<!-- BEGIN:{name} -->).*?(<!-- END:{name} -->)",
        re.DOTALL,
    )
    replacement = f"<!-- BEGIN:{name} -->\n{new_body.strip()}\n<!-- END:{name} -->"
    result, count = pattern.subn(replacement, content)
    if count == 0:
        print(f"  ⚠️  Marker {name} not found in note — skipping")
    return result


# ---------------------------------------------------------------------------
# kubectl helpers
# ---------------------------------------------------------------------------

def kubectl(*args, context: str = None) -> dict | list:
    """Run a kubectl command and return parsed JSON output."""
    cmd = ["kubectl"]
    if context:
        cmd += ["--context", context]
    cmd += list(args)
    cmd += ["-o", "json"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"kubectl {' '.join(args)} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def get_k3s_nodes(context: str) -> str:
    """Build the k3s nodes markdown table from live kubectl data."""
    data = kubectl("get", "nodes", "-o", "wide", context=context)

    # We need wide output columns — use custom columns instead of JSON for simplicity
    cmd = [
        "kubectl", "--context", context,
        "get", "nodes",
        "--no-headers",
        "-o", "custom-columns="
        "NAME:.metadata.name,"
        "STATUS:.status.conditions[-1].type,"
        "VERSION:.status.nodeInfo.kubeletVersion,"
        "IP:.status.addresses[?(@.type==\"InternalIP\")].address,"
        "OS:.status.nodeInfo.osImage,"
        "RUNTIME:.status.nodeInfo.containerRuntimeVersion",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"kubectl get nodes failed: {result.stderr.strip()}")

    rows = []
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        name, _status, version, ip = parts[0], parts[1], parts[2], parts[3]
        # OS image may have spaces — rejoin from index 4, split off runtime at end
        runtime = parts[-1]
        os_image = " ".join(parts[4:-1])
        rows.append((name, ip, os_image, runtime, version))

    if not rows:
        raise RuntimeError("No nodes returned from kubectl")

    header = (
        "| Node        | IP          | OS                 | Runtime               | Version      |\n"
        "| ----------- | ----------- | ------------------ | --------------------- | ------------ |"
    )
    table_rows = "\n".join(
        f"| {name:<11} | {ip:<11} | {os:<18} | {runtime:<21} | {version:<12} |"
        for name, ip, os, runtime, version in sorted(rows)
    )
    return f"{header}\n{table_rows}"



# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

def ssh_run(host: str, command: str, user: str = "root", key_path: str = "", timeout: int = 10) -> str:
    """Run a command on a remote host via SSH and return stdout."""
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
           "-o", f"ConnectTimeout={timeout}"]
    if key_path:
        cmd += ["-i", key_path]
    cmd += [f"{user}@{host}", command]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    if result.returncode != 0:
        raise RuntimeError(f"SSH to {host} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_zfs_pools(host: str, user: str, key_path: str, timeout: int) -> str:
    """Build the ZFS storage markdown table from live zpool data on pve15."""
    # -H: no header, -p: exact (parseable) numbers, fields: name, size, alloc, free
    output = ssh_run(
        host,
        "zpool list -H -p -o name,size,alloc,free",
        user=user,
        key_path=key_path,
        timeout=timeout,
    )

    # Static config info we already know (not returned by zpool list)
    pool_meta = {
        "rpool":   ("ZFS mirror",  "2x NVMe"),
        "SSDPool": ("ZFS RAIDZ2", "4x SSD"),
        "HDDPool": ("ZFS RAIDZ2", "4x HDD"),
    }

    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name, size_b, alloc_b, free_b = parts[0], int(parts[1]), int(parts[2]), int(parts[3])

        def fmt(b: int) -> str:
            for unit in ("B", "K", "M", "G", "T"):
                if b < 1024:
                    return f"{b:.1f}{unit}"
                b /= 1024
            return f"{b:.1f}P"

        pool_type, config = pool_meta.get(name, ("ZFS", "—"))
        rows.append((name, pool_type, fmt(size_b * 1024), fmt(free_b * 1024), config))

    if not rows:
        raise RuntimeError(f"No ZFS pools returned from {host}")

    header = (
        "| Pool    | Type       | Size   | Free | Configuration |\n"
        "| ------- | ---------- | ------ | ---- | ------------- |"
    )
    table_rows = "\n".join(
        f"| {name:<7} | {ptype:<10} | {size:<6} | {free:<4} | {config:<13} |"
        for name, ptype, size, free, config in rows
    )
    return f"{header}\n{table_rows}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SECTIONS = ["last-refreshed", "k3s-nodes", "zfs-storage"]


def main():
    parser = argparse.ArgumentParser(
        description="Refresh the Home Lab note with live infrastructure data"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be updated without writing the file",
    )
    parser.add_argument(
        "--section", choices=SECTIONS,
        help="Refresh only a specific section (default: all)",
    )
    args = parser.parse_args()

    note_path = NOTE_PATH
    print(f"Note: {note_path}")
    print(f"k3s context: {K3S_CONTEXT}")
    print(f"ZFS host: {PVE_SSH_USER}@{PVE_STORAGE_HOST}")
    print()

    try:
        with open(note_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Note not found at {note_path}")
        print("Set NOTE_PATH in .env to the correct path.")
        sys.exit(1)

    errors = []
    refresh_all = args.section is None

    # --- k3s nodes ---
    if refresh_all or args.section == "k3s-nodes":
        print("🔄 Fetching k3s node info...")
        try:
            table = get_k3s_nodes(K3S_CONTEXT)
            content = replace_section(content, "K3S_NODES", table)
            print("  ✅ k3s nodes updated")
        except Exception as e:
            print(f"  ❌ k3s nodes failed: {e}")
            errors.append(str(e))

    # --- ZFS storage ---
    if refresh_all or args.section == "zfs-storage":
        print(f"🔄 Fetching ZFS pool info from {PVE_STORAGE_HOST}...")
        try:
            table = get_zfs_pools(PVE_STORAGE_HOST, PVE_SSH_USER, SSH_KEY_PATH, SSH_TIMEOUT)
            content = replace_section(content, "ZFS_STORAGE", table)
            print("  ✅ ZFS storage updated")
        except Exception as e:
            print(f"  ❌ ZFS storage failed: {e}")
            errors.append(str(e))

    # --- Last refreshed timestamp ---
    if refresh_all or args.section == "last-refreshed":
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        status = " (some sections failed)" if errors else ""
        refreshed_line = f"*Live data last refreshed: {now}{status} — run `homelab-refresh-note.py` to update*"
        content = replace_section(content, "LAST_REFRESHED", refreshed_line)

    if args.dry_run:
        print()
        print("--- DRY RUN: note content would be written as follows ---")
        print(content[:2000], "..." if len(content) > 2000 else "")
    else:
        with open(note_path, "w") as f:
            f.write(content)
        print()
        print(f"✅ Note written to {note_path}")

    if errors:
        print(f"\n⚠️  {len(errors)} section(s) failed — note updated with available data")
        sys.exit(1)


if __name__ == "__main__":
    main()
