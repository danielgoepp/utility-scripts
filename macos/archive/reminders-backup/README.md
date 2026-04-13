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

### plist example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dang.export-reminders</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>OUTDIR=/Users/dang/Documents/Household/General/Reminders; PYTHON=/Users/dang/Documents/Development/utility-scripts/.venv/bin/python3; SCRIPT=/Users/dang/Documents/Development/utility-scripts/macos/export-reminders.py; $PYTHON $SCRIPT -f json -o $OUTDIR/reminders-$(date +%Y-%m-%d).json &amp;&amp; $PYTHON $SCRIPT -f csv -o $OUTDIR/reminders-$(date +%Y-%m-%d).csv &amp;&amp; find $OUTDIR -name 'reminders-*' -mtime +3 -delete</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/export-reminders.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/export-reminders.log</string>
</dict>
</plist>
```