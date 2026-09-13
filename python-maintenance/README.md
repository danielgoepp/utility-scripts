# Python Maintenance

Upgrades outdated Python packages across the Homebrew system Python and every
project venv found under a scan root (default `~/Development`).

## Setup

Copy `.env.example` to `.env` and fill in your values (only needed for
`--email`):

```bash
cp python-maintenance/.env.example python-maintenance/.env
```

Because this script imports `config.py` (which uses `python-dotenv`), run it
with a Python that has that package installed — the repo's own `.venv` already
does:

```bash
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Usage

```bash
python3 python-maintenance/update-python-libraries.py -h
```

Common flags:

- `--dry-run` — list outdated packages without upgrading anything
- `--system-only` / `--venvs-only` — restrict to one side
- `--scan-root PATH` — change where project venvs are searched for
- `--email` — email a summary of the run to `TO_EMAIL` via the SMTP settings
  in `.env`

Packages that Homebrew itself vendors into the system Python (e.g. `wheel`)
can't be cleanly upgraded via `pip install --upgrade` — pip has no install
record for them. The script detects this and reports it as a skip rather
than a failure; update those via `brew upgrade python@3.x` instead.

## Scheduling with launchd (macOS)

Templates for running this weekly via `launchd` are in `launchd/`. To install:

1. Copy the wrapper script and fill in your paths:

   ```bash
   cp python-maintenance/launchd/run-python-maintenance.sh ~/.local/bin/
   chmod +x ~/.local/bin/run-python-maintenance.sh
   # edit SCRIPT and PYTHON_BIN in the copied script
   # PYTHON_BIN must point at a Python with python-dotenv installed
   # (the repo's own .venv works) since the script needs it for --email
   ```

2. Copy the plist, rename it to your own label, and fill in your paths:

   ```bash
   cp python-maintenance/launchd/com.example.python-maintenance.plist \
      ~/Library/LaunchAgents/com.yourdomain.python-maintenance.plist
   # edit Label, ProgramArguments, and the log paths
   ```

3. Load it:

   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourdomain.python-maintenance.plist
   ```

4. Test it immediately instead of waiting for the schedule:

   ```bash
   launchctl kickstart gui/$(id -u)/com.yourdomain.python-maintenance
   tail -f ~/Library/Logs/python-maintenance.log
   ```

To change the schedule, edit `StartCalendarInterval` in the plist, then
re-bootstrap (`launchctl bootout` followed by `launchctl bootstrap`) for the
change to take effect.
