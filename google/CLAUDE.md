# CLAUDE.md — Google API Scripts

This directory contains Python scripts for interacting with Google Workspace APIs (Calendar, etc.).

## Authentication

Google API access uses OAuth2. The auth flow is:

1. **`credentials.json`** — Downloaded from the [Google Cloud Console](https://console.cloud.google.com/). Navigate to **APIs & Services > Credentials**, create or select a **Desktop app** OAuth client, and download the JSON. Place it at `google/credentials.json`. This file is gitignored and must never be committed.

2. **`token.json`** — Generated automatically on first login by running `auth.py`. Stores the access and refresh tokens so subsequent scripts do not require browser login. Also gitignored.

3. **`auth.py`** — Run this once to perform the initial OAuth browser login and generate `token.json`. Re-run it (after deleting `token.json`) whenever scopes change.

### First-time setup

```bash
# 1. Download credentials.json from Google Cloud Console and place at google/credentials.json
# 2. Enable the relevant Google API(s) in the Cloud Console under APIs & Services > Library
# 3. Install dependencies and authenticate
source .venv/bin/activate
pip3 install -r requirements.txt
python3 google/auth.py
```

## Configuration

- **`config.py`** — Defines credential file paths and OAuth scopes
- **`.env`** — Optionally overrides default file paths (see `.env.example`)
- **`SCOPES`** in `config.py` — Add additional OAuth scopes here when new Google APIs are integrated. After changing scopes, delete `token.json` and re-run `auth.py`

## File Structure

```
google/
├── CLAUDE.md             # This file
├── config.py             # Paths and scopes
├── auth.py               # OAuth login helper (run once)
├── list-calendars.py     # List all Google calendars
├── delete-calendar.py    # Delete or unsubscribe from a calendar
├── .env                  # Optional path overrides (gitignored)
├── .env.example          # Template
├── credentials.json      # Downloaded from Google Cloud Console (gitignored)
└── token.json            # Generated after first login (gitignored)
```

## Adding New Google APIs

1. Enable the API in Google Cloud Console under **APIs & Services > Library**
2. Add the required OAuth scope(s) to `SCOPES` in `config.py`
3. Delete `google/token.json` and re-run `python3 google/auth.py` to re-authenticate
4. Import `get_credentials` from `auth.py` and `build` from `googleapiclient.discovery` in the new script

## Running Scripts

All scripts must be run from the repository root with the virtual environment active:

```bash
source .venv/bin/activate
python3 google/list-calendars.py
python3 google/list-calendars.py --show-hidden
python3 google/delete-calendar.py
python3 google/delete-calendar.py --id <calendarId>
python3 google/delete-calendar.py --id <calendarId> --remove-from-list
```

## Script Reference

| Script | Description |
| --- | --- |
| `auth.py` | OAuth login — run once to generate `token.json` |
| `list-calendars.py` | List all calendars (ID, access role, time zone) |
| `delete-calendar.py` | Permanently delete an owned calendar, or remove/unsubscribe from any calendar |

## Google API Limitations

- **System-managed calendars** (e.g. Birthdays) cannot be deleted or removed from the calendar list via the API, even if you are the owner. This is a Google platform restriction with no known workaround.
- The **primary calendar** cannot be deleted or removed.
- `deleted` is a read-only field on calendarList resources — it cannot be set via the API.
