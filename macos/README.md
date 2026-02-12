# macOS Utilities

## export-reminders.py

Exports all macOS Reminders to JSON and/or CSV. Uses the native EventKit framework via `pyobjc-framework-EventKit` for fast, direct database access (no Apple Event IPC).

### Dependencies

```bash
pip install pyobjc-framework-EventKit
```

### Usage

```bash
python3 export-reminders.py -f json -o reminders.json
python3 export-reminders.py -f csv -o reminders.csv
python3 export-reminders.py --stdout -f json
python3 export-reminders.py --incomplete-only --list "Errands" --stdout
```

On first run, macOS will prompt for Reminders access. If denied, grant access in **System Settings > Privacy & Security > Reminders**.

### Scheduled Export (launchd)

A launchd job is installed at `~/Library/LaunchAgents/com.dang.export-reminders.plist` that:

- Runs daily at 5:00 AM
- Exports both JSON and CSV to `/Users/dang/Documents/Household/General/Reminders/`
- Files are named `reminders-YYYY-MM-DD.json` and `reminders-YYYY-MM-DD.csv`
- Purges export files older than 3 days
- Logs to `/tmp/export-reminders.log`

Management commands:

```bash
# Reload after editing the plist
launchctl unload ~/Library/LaunchAgents/com.dang.export-reminders.plist
launchctl load ~/Library/LaunchAgents/com.dang.export-reminders.plist

# Trigger a manual run
launchctl start com.dang.export-reminders

# Check logs
cat /tmp/export-reminders.log
```
