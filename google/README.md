# Google API Scripts

Python scripts for interacting with Google Workspace APIs.

## Prerequisites

- Python 3.10+
- A Google account
- A Google Cloud project with the relevant API(s) enabled

---

## One-Time Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)

### 2. Enable the Google Calendar API

1. In the Cloud Console, go to **APIs & Services > Library**
2. Search for **Google Calendar API** and click **Enable**

### 3. Configure the OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **Internal** for audience (if using a Google Workspace account) or **External**
3. Fill in the app name and support email, then save

### 4. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Desktop app** as the application type
4. Download the resulting JSON file
5. Save it as `google/credentials.json` in this repository

### 5. Install Dependencies

```bash
source .venv/bin/activate
pip3 install -r requirements.txt
```

### 6. Authenticate

Run the auth script once. It will open a browser window asking you to log in with your Google account and grant access:

```bash
source .venv/bin/activate
python3 google/auth.py
```

A `token.json` file will be saved automatically. Future scripts will use this token without requiring login again.

---

## Scripts

### `list-calendars.py`

Lists all calendars on the authenticated Google account.

```bash
python3 google/list-calendars.py

# Include hidden calendars
python3 google/list-calendars.py --show-hidden
```

Example output:

```text
Found 3 calendar(s):

  dan@goepp.com [PRIMARY]
    ID:          dan@goepp.com
    Access role: owner
    Time zone:   America/New_York

  Holidays in United States
    ID:          en.usa#holiday@group.v.calendar.google.com
    Access role: reader
    Time zone:   America/New_York
```

---

### `delete-calendar.py`

Deletes or unsubscribes from a calendar. A confirmation prompt is always shown before any action is taken.

For **owned** calendars you are prompted to choose between:

- **Permanently delete** — removes the calendar and all its events forever
- **Remove from list** — hides it from your account without deleting the underlying calendar

For **non-owned** calendars (reader, writer) the only option is to remove it from your list (unsubscribe).

The primary calendar cannot be deleted or removed.

```bash
# Interactive: lists calendars and prompts you to pick one
python3 google/delete-calendar.py

# Direct: specify a calendar ID to skip selection
python3 google/delete-calendar.py --id <calendarId>

# Skip the delete/remove prompt and force remove-from-list only
python3 google/delete-calendar.py --id <calendarId> --remove-from-list
```

> **Note:** Google system-managed calendars (e.g. Birthdays) cannot be deleted or removed via the API regardless of ownership. This is a Google platform restriction with no workaround.

---

## Re-authenticating

If your token expires or you need to change permissions, delete `token.json` and run the auth script again:

```bash
rm google/token.json
python3 google/auth.py
```

---

## Security Notes

- `credentials.json` and `token.json` are sensitive — do not commit them to git
- `credentials.json` can be revoked at any time from [Google Cloud Console > Credentials](https://console.cloud.google.com/apis/credentials)
- `token.json` can be revoked by removing the app from your [Google Account permissions](https://myaccount.google.com/permissions)
