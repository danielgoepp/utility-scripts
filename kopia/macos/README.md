# Kopia macOS Launchd Setup

KopiaUI does not natively catch up missed backups when a Mac wakes from sleep. The solution is to disable scheduling in the KopiaUI policy and instead use launchd agents with `StartCalendarInterval`, which automatically fires missed runs the next time the Mac is awake.

One agent is created per repository, staggered 15 minutes apart to avoid simultaneous resource contention.

**Schedule:** 9:00am, 1:00pm, 5:00pm, 9:00pm (staggered per repo)

## Why StartCalendarInterval (not cron)

Unlike cron, launchd's `StartCalendarInterval` tracks missed jobs. If the Mac was asleep at the scheduled time, launchd fires the job once on the next wake. Multiple missed intervals collapse into a single catch-up run.

## Prerequisites

- KopiaUI installed and repositories connected
- Scheduling **disabled** in the Kopia policy for each repo (let launchd own the schedule)
- `kopia` CLI binary available via Homebrew (recommended) or bundled inside KopiaUI

```bash
brew install kopia
```

## Files

| File                     | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `kopia-launchd-setup.sh` | Setup script — run this to install or update agents  |

The following are generated automatically by the setup script and are not tracked in git:

| Generated file                                         | Purpose                                                 |
|--------------------------------------------------------|---------------------------------------------------------|
| `~/.local/bin/run-kopia-<name>.sh`                     | Wrapper script per repo — adds timestamps to log output |
| `~/Library/LaunchAgents/com.kopia.backup.<name>.plist` | Launchd agent per repo                                  |

## Setup

```bash
chmod +x kopia-launchd-setup.sh
./kopia-launchd-setup.sh
```

The script will:

- Auto-detect the `kopia` binary
- Discover all repository configs in `~/Library/Application Support/kopia/`
- Read the `description` field from each config to use as a friendly agent name
- Generate a wrapper script and launchd plist for each repo
- Install and load all agents
- Optionally run a test snapshot immediately

Re-running the script is safe — it unloads and reloads agents before regenerating.

Wrapper scripts are installed to `~/.local/bin`. Ensure this is in your `PATH` — add to `~/.zshrc` if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Log Output

Each backup run is wrapped with timestamps:

```text
=== 2026-03-30 09:00:02 Starting kopia snapshot (Kopia SSD) ===
Snapshotting dang@daniel-mbp:/Users/dang ...
 * 0 hashing, 80 hashed (2.2 MB), 93479 cached (26.9 GB), uploaded 2.6 MB ...
Created snapshot with root k... in 1m7s
=== 2026-03-30 09:01:09 Snapshot completed successfully ===
```

## macOS Privacy Permissions

Kopia requires **Full Disk Access** to snapshot protected locations like the Photos Library. Without it, you'll see:

```text
! Error when processing "Pictures/Photos Library.photoslibrary": cannot create iterator:
  unable to read directory: open /Users/dang/Pictures/Photos Library.photoslibrary: operation not permitted
```

**To grant access:**

- System Settings → Privacy & Security → Full Disk Access
- Click `+` and add `/opt/homebrew/bin/kopia` (use Cmd+Shift+G in the file picker to navigate to the path)
- Also add your terminal app (e.g. iTerm2) if you want to run snapshots manually from the terminal

> **Note:** Each terminal app has its own FDA grant. If you see the Photos Library error when running kopia manually, check which terminal you're using — it may not have FDA even if the kopia binary does. The launchd agents are unaffected by this since they run independently of any terminal.

## Useful Commands

```bash
# Check agents are loaded
launchctl list | grep com.kopia

# Trigger a backup manually (without waiting for schedule)
launchctl start com.kopia.backup.<name>

# View logs
tail -f ~/Library/Logs/kopia-<name>.log

# Reload after editing a wrapper script
launchctl unload ~/Library/LaunchAgents/com.kopia.backup.<name>.plist
launchctl load   ~/Library/LaunchAgents/com.kopia.backup.<name>.plist
```

## File Locations

```text
~/Library/Application Support/kopia/*.config    # repo configs (one per connected repo)
~/.local/bin/run-kopia-*.sh                     # generated wrapper scripts
~/Library/LaunchAgents/com.kopia.backup.*.plist # generated agents
~/Library/Logs/kopia-*.log                      # log files
```

## Adapting for Another Mac

Run `kopia-launchd-setup.sh` on the new Mac after connecting repositories in KopiaUI. The script discovers configs automatically — no manual path editing required.

## Notes

- `--all` snapshots all sources defined in the Kopia policy; no need to hardcode paths
- `RunAtLoad false` prevents an immediate backup when the agent is first loaded
- KopiaUI can remain installed for browsing snapshots — it won't conflict as long as its own scheduling is disabled in the policy
