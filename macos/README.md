# macOS

## Installed applications note

`update-installed-apps-note.py` keeps a Markdown note (e.g. in Obsidian) of the
apps, Homebrew packages, and scheduled launchd jobs on this Mac. See the main
README for what it records and how the note is updated.

```bash
cp macos/.env.example macos/.env   # set INSTALLED_APPS_NOTE
source .venv/bin/activate
python3 macos/update-installed-apps-note.py --dry-run
```

### Scheduling with launchd

Templates for running this daily via `launchd` are in `launchd/`. The job runs
at 6:00am; if the Mac is asleep then, launchd runs it on the next wake. It also
runs at login, to cover days the Mac was shut down rather than asleep.

1. Copy the wrapper script and fill in your paths:

   ```bash
   cp macos/launchd/run-installed-apps-note.sh ~/.local/bin/
   chmod +x ~/.local/bin/run-installed-apps-note.sh
   # edit SCRIPT and PYTHON_BIN in the copied script
   # PYTHON_BIN must point at a Python with python-dotenv installed
   # (the repo's own .venv works)
   ```

2. Copy the plist, rename it to your own label, and fill in your paths:

   ```bash
   cp macos/launchd/com.example.installed-apps-note.plist \
      ~/Library/LaunchAgents/com.yourdomain.installed-apps-note.plist
   # edit Label, ProgramArguments, and the log paths
   ```

3. Load it (because of `RunAtLoad`, this also runs it once immediately):

   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourdomain.installed-apps-note.plist
   ```

4. Check the result, or re-run it on demand:

   ```bash
   tail ~/Library/Logs/installed-apps-note.log
   launchctl kickstart gui/$(id -u)/com.yourdomain.installed-apps-note
   ```

To change the schedule, edit `StartCalendarInterval` in the plist, then
re-bootstrap (`launchctl bootout` followed by `launchctl bootstrap`) for the
change to take effect.
