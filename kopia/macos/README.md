# Kopia macOS Launchd Setup

KopiaUI does not natively catch up missed backups when a Mac wakes from sleep. The solution is to disable scheduling in the KopiaUI policy and instead use launchd agents with `StartCalendarInterval`, which automatically fires missed runs the next time the Mac is awake.

Two agents are used — one per repository — staggered 15 minutes apart to avoid simultaneous resource contention.

**Repositories:**
- `com.kopia.backup.ssd` → Local Kopia Repository Server
- `com.kopia.backup.b2` → Backblaze B2

**Schedule:** 9:00am, 1:00pm, 5:00pm, 9:00pm (B2 runs 15 min later)

## Why StartCalendarInterval (not cron)

Unlike cron, launchd's `StartCalendarInterval` tracks missed jobs. If the Mac was asleep at the scheduled time, launchd fires the job once on the next wake. Multiple missed intervals collapse into a single catch-up run.

## Prerequisites

- KopiaUI installed and repositories connected
- Scheduling **disabled** in the Kopia policy for each repo (let launchd own the schedule)
- `kopia` CLI binary available (bundled inside KopiaUI or via Homebrew)

```bash
# Find the kopia binary bundled with KopiaUI
find /Applications/KopiaUI.app -name "kopia" -type f

# Or install via Homebrew
brew install kopia
```

## Files

| File | Purpose |
|------|---------|
| `kopia-launchd-setup.sh` | One-time (or idempotent) setup script — installs and loads agents |
| `com.kopia.backup.ssd.plist` | Launchd agent definition for SSD repo |
| `com.kopia.backup.b2.plist` | Launchd agent definition for B2 repo |
| `run-kopia-ssd.sh` | Wrapper script — adds timestamps to SSD log output |
| `run-kopia-b2.sh` | Wrapper script — adds timestamps to B2 log output |

## Setup

Place all files in the same directory, then run:

```bash
chmod +x kopia-launchd-setup.sh
./kopia-launchd-setup.sh
```

The script will:
1. Auto-detect the `kopia` binary
2. Install plists to `~/Library/LaunchAgents/`
3. Validate and load the agents
4. Optionally run a test snapshot immediately

> **Note:** The kopia binary path is set directly in the wrapper scripts (`run-kopia-ssd.sh`, `run-kopia-b2.sh`), not in the plists. Update those scripts if the binary location changes.

## Log Output

Each backup run is wrapped with timestamps:

```
=== 2026-03-30 09:00:02 Starting kopia SSD snapshot ===
Snapshotting dang@daniel-mbp:/Users/dang ...
 * 0 hashing, 80 hashed (2.2 MB), 93479 cached (26.9 GB), uploaded 2.6 MB ...
Created snapshot with root k... in 1m7s
=== 2026-03-30 09:01:09 Snapshot completed successfully ===
```

## macOS Privacy Permissions

Kopia requires **Full Disk Access** to snapshot protected locations like the Photos Library. Without it, you'll see:

```
! Error when processing "Pictures/Photos Library.photoslibrary": cannot create iterator:
  unable to read directory: open /Users/dang/Pictures/Photos Library.photoslibrary: operation not permitted
```

**To grant access:**
1. System Settings → Privacy & Security → Full Disk Access
2. Click `+` and add `/opt/homebrew/bin/kopia` (use Cmd+Shift+G in the file picker to navigate to the path)
3. Also add your terminal app (e.g. iTerm2) if you want to run snapshots manually from the terminal

> **Note:** Each terminal app has its own FDA grant. If you see the Photos Library error when running kopia manually, check which terminal you're using — it may not have FDA even if the kopia binary does. The launchd agents are unaffected by this since they run independently of any terminal.

## Useful Commands

```bash
# Check agents are loaded
launchctl list | grep com.kopia

# Trigger a backup manually (without waiting for schedule)
launchctl start com.kopia.backup.ssd
launchctl start com.kopia.backup.b2

# View logs
tail -f ~/Library/Logs/kopia-ssd.log
tail -f ~/Library/Logs/kopia-b2.log

# Reload after editing a plist or wrapper script
launchctl unload ~/Library/LaunchAgents/com.kopia.backup.ssd.plist
launchctl load   ~/Library/LaunchAgents/com.kopia.backup.ssd.plist
```

## File Locations

```
~/Library/Application Support/kopia/repository.config               # SSD repo config
~/Library/Application Support/kopia/repository-1680706950621.config # B2 repo config
~/Library/LaunchAgents/com.kopia.backup.ssd.plist
~/Library/LaunchAgents/com.kopia.backup.b2.plist
~/Library/Logs/kopia-ssd.log
~/Library/Logs/kopia-b2.log
```

## Adapting for Another Mac

Same setup — change the username in the wrapper scripts and plist paths:
- `/Users/dang/` → `/Users/username/`
- Config filenames stay the same if connecting to the same repos

## Notes

- `--all` snapshots all sources defined in the Kopia policy; no need to hardcode paths
- `RunAtLoad false` prevents an immediate backup when the agent is first loaded
- KopiaUI can remain installed for browsing snapshots — it won't conflict as long as its own scheduling is disabled in the policy
