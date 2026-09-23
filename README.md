# Utility Scripts

A collection of Python utility scripts for managing and maintaining various infrastructure and home automation services.

## Quick Start

```bash
source .venv/bin/activate
pip3 install -r requirements.txt
```

Copy and fill in the relevant `.env.example` for each service you want to use:

```bash
cp <service>/.env.example <service>/.env
```

Run any script with `-h` for usage details:

```bash
python3 <service>/<script>.py -h
```

## Services

### 1Password

- `set-autofill-behavior.py` - Set the per-URL autofill behavior (e.g. "Only on this exact host") for every item with a URL on the configured domains, so logins for internal hosts sharing a parent domain stop being offered on each other; dry run by default, `--apply` to write. Uses the 1Password SDK with desktop app authentication (enable Settings > Developer > "Integrate with other apps"). Items containing fields the SDK cannot edit (e.g. legacy saved web-form fields) are skipped and reported for manual change in the app

### AlertManager

- `alertmanager-maintenance.py` - Manage Prometheus AlertManager silences and maintenance windows

### Cloudflare

- `cf-clear-stale-acme.py` - Clean up stale ACME challenge DNS records

### Google

- `list-calendars.py` - List Google Calendars
- `delete-calendar.py` - Delete a Google Calendar

### Grafana

- `grafana-get-datasources.py` - List configured datasources

### Graylog

- `graylog-maintenance.py` - Manage Graylog maintenance mode

### Home Assistant

- `get-automations.py` - Export automations
- `get-config.py` - Retrieve HA configuration
- `get-devices.py` - List entity states, with filters for unavailable/unknown entities
- `get-entities.py` - List entities
- `get-light-settings.py` - Export light entity settings
- `ha-automation-filter.py` - Filter automations by criteria
- `ha-remote-restart.py` - Remotely restart Home Assistant

### Kopia

- `kopia-check-backups.py` - Check backup health across Kopia instances

### macOS

- `export-contacts.py` - Export macOS Contacts to CSV
- `MacOS Mount SMB.scpt` - AppleScript for automating SMB share mounts

### Network

- `network-scan.py` - Scan network and analyze discovered hosts

### OpenSearch

- `opensearch-field-count.py` - Report field counts across indices
- `opensearch-purge-top-queries.py` - Purge top queries data

### OPNsense

- `opnsense-dnsmasq-leases.py` - List DHCP leases served by dnsmasq, including configured host reservations with no active lease (use `--no-reservations` to show active leases only, or `--if-descr LAN` to limit output to a single interface)
- `opnsense-dnsmasq-reserve-by-hostname.py` - Interactively create dnsmasq host reservations for leases matching a hostname substring, assigned sequentially from a chosen starting IP (no arguments; prompts for input and reloads dnsmasq automatically)

### Python Maintenance

- `update-python-libraries.py` - Upgrade outdated packages across the Homebrew system Python and all project venvs found under a scan root

### Todoist

- `download-backup.py` - Download Todoist backups
- `setup-oauth.py` - Set up Todoist OAuth credentials

### UniFi

- `unifi-device-list.py` - List UniFi hardware devices (cloud API)
- `unifi-list-online-clients.py` - List currently online client devices (local API)
- `unifi-delete-offline-clients.py` - Remove offline client devices from UniFi

### Uptime Kuma

- `uptime-kuma-export.py` - Export monitor configuration
- `uptime-kuma-import.py` - Import monitor configuration
- `uptime-kuma-maintenance.py` - Manage maintenance windows
- `uptime-kuma-enable-notifications.py` - Bulk enable notifications
- `uptime-kuma-disable-group-notifications.py` - Disable notifications on all group monitors
- `uptime-kuma-set-group-retries.py` - Set retry count for all monitors in a parent group
- `uptime-kuma-set-default-retries.py` - Set retry count for all monitors

### Zigbee2MQTT

- `z2m-get-devices.py` - List Zigbee devices
- `z2m-get-color-mode.py` - Query color mode for light devices
- `z2m-monitor-device.py` - Monitor a specific device's MQTT messages
- `mqtt-test.py` - Basic MQTT publish/subscribe testing

## Architecture

Each service directory follows a consistent pattern:

```text
service/
├── config.py          # Environment variable configuration
├── service-script.py  # Main functionality
├── .env              # Local environment variables (gitignored)
└── .env.example      # Template for required variables
```

Configuration is managed via `python-dotenv` — credentials and URLs stay in `.env` files, never in code.
