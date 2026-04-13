# Todoist Backup Downloader

Downloads the most recent Todoist backup. Intended to run daily via cron or a scheduler.

## Requirements

Two tokens are required due to how Todoist's API works:

- **`TODOIST_OAUTH_TOKEN`** — used to list available backups. The backups endpoint requires an OAuth token with the `backups:read` scope (bypasses MFA). Obtained once via `setup-oauth.py`.
- **`TODOIST_API_TOKEN`** — used to download the backup file. Your personal API token from Settings > Integrations > Developer.

## Setup

### 1. Create a Todoist OAuth app

Go to https://app.todoist.com/app/settings/integrations/app-management and create a new app. Set the redirect URI to `https://localhost`.

### 2. Configure `.env`

Copy `.env.example` to `.env` and fill in your values:

```
TODOIST_API_TOKEN=your-personal-api-token
TODOIST_CLIENT_ID=your-client-id
TODOIST_CLIENT_SECRET=your-client-secret
TODOIST_OAUTH_REDIRECT_URI=https://localhost
```

### 3. Run OAuth setup (one time)

```bash
python3 todoist/setup-oauth.py
```

Open the printed URL in your browser and authorize. Your browser will redirect to `https://localhost` (a connection error is expected). Copy the full URL from the address bar and run:

```bash
python3 todoist/setup-oauth.py --complete "<redirect url>"
```

This saves `TODOIST_OAUTH_TOKEN` to `.env`. You won't need to repeat this step.

## Usage

```bash
source .venv/bin/activate
python3 todoist/download-backup.py
```

By default, backups are saved to `~/Downloads`. To specify a different directory:

```bash
python3 todoist/download-backup.py --output-dir ~/backups/todoist
```

If the most recent backup has already been downloaded, it will be skipped.
