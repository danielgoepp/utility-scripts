#!/usr/bin/env python3
"""One-time OAuth setup for Todoist backups access.

The Todoist backups endpoint requires an OAuth token with the `backups:read`
scope. Run this script once to obtain and save that token to .env.

Setup:
    1. Go to https://app.todoist.com/app/settings/integrations/app-management
       and create a new app. Set the redirect URI to any value, e.g.:
           https://localhost
    2. Copy the Client ID, Client Secret, and redirect URI into todoist/.env:
           TODOIST_CLIENT_ID=...
           TODOIST_CLIENT_SECRET=...
           TODOIST_OAUTH_REDIRECT_URI=https://localhost
    3. Run to get the authorization URL:
           python3 todoist/setup-oauth.py
    4. Open the URL in your browser, authorize, then copy the redirect URL
       (it may show a connection error — that's fine) and run:
           python3 todoist/setup-oauth.py --complete "<redirect url>"
"""

import argparse
import os
import secrets
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE)

TODOIST_CLIENT_ID = os.getenv("TODOIST_CLIENT_ID")
TODOIST_CLIENT_SECRET = os.getenv("TODOIST_CLIENT_SECRET")
TODOIST_OAUTH_REDIRECT_URI = os.getenv("TODOIST_OAUTH_REDIRECT_URI", "https://localhost")

OAUTH_AUTHORIZE_URL = "https://app.todoist.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://api.todoist.com/oauth/access_token"
OAUTH_SCOPE = "backups:read"


def step1_print_auth_url():
    if not TODOIST_CLIENT_ID or not TODOIST_CLIENT_SECRET:
        print(
            "Error: TODOIST_CLIENT_ID and TODOIST_CLIENT_SECRET must be set in .env\n"
            "\n"
            "Steps:\n"
            "  1. Visit https://app.todoist.com/app/settings/integrations/app-management\n"
            "  2. Create a new app. Set the redirect URI to any HTTPS URL, e.g. https://localhost\n"
            "  3. Add to todoist/.env:\n"
            "       TODOIST_CLIENT_ID=...\n"
            "       TODOIST_CLIENT_SECRET=...\n"
            "       TODOIST_OAUTH_REDIRECT_URI=https://localhost\n"
            "  4. Re-run: python3 todoist/setup-oauth.py",
            file=sys.stderr,
        )
        sys.exit(1)

    state = secrets.token_urlsafe(16)
    set_key(ENV_FILE, "TODOIST_OAUTH_STATE", state)

    params = {
        "client_id": TODOIST_CLIENT_ID,
        "scope": OAUTH_SCOPE,
        "state": state,
        "redirect_uri": TODOIST_OAUTH_REDIRECT_URI,
    }
    auth_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    print("Open this URL in your browser to authorize:\n")
    print(f"  {auth_url}\n")
    print(
        f"After authorizing, your browser will redirect to {TODOIST_OAUTH_REDIRECT_URI}\n"
        "(it may show a connection error — that's fine).\n"
        "Copy the full URL from the address bar, then run:\n\n"
        '  python3 todoist/setup-oauth.py --complete "<redirect url>"'
    )


def step2_exchange_code(redirect_url):
    saved_state = os.getenv("TODOIST_OAUTH_STATE")

    parsed = urlparse(redirect_url)
    qs = parse_qs(parsed.query)
    code = qs.get("code", [None])[0]
    returned_state = qs.get("state", [None])[0]

    if not code:
        print("Error: no authorization code found in the URL.", file=sys.stderr)
        sys.exit(1)

    if saved_state and returned_state != saved_state:
        print("Error: state mismatch — the URL may not match this session.", file=sys.stderr)
        sys.exit(1)

    print("Exchanging code for access token...")
    resp = requests.post(
        OAUTH_TOKEN_URL,
        json={
            "client_id": TODOIST_CLIENT_ID,
            "client_secret": TODOIST_CLIENT_SECRET,
            "code": code,
            "redirect_uri": TODOIST_OAUTH_REDIRECT_URI,
        },
        timeout=10,
    )
    resp.raise_for_status()
    access_token = resp.json()["access_token"]

    set_key(ENV_FILE, "TODOIST_OAUTH_TOKEN", access_token)
    set_key(ENV_FILE, "TODOIST_OAUTH_STATE", "")
    print(f"OAuth token saved to {ENV_FILE}")
    print("Setup complete. You can now run download-backup.py.")


def main():
    parser = argparse.ArgumentParser(description="One-time OAuth setup for Todoist backups")
    parser.add_argument(
        "--complete",
        metavar="REDIRECT_URL",
        help="Pass the redirect URL from the browser to complete setup and save the OAuth token",
    )
    args = parser.parse_args()

    if args.complete:
        step2_exchange_code(args.complete)
    else:
        step1_print_auth_url()


if __name__ == "__main__":
    main()
