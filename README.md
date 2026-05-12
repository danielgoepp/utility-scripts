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

- `devices-list.py` - List all devices
- `get-automations.py` - Export automations
- `get-config.py` - Retrieve HA configuration
- `get-entities.py` - List entities
- `get-light-settings.py` - Export light entity settings
- `ha-automation-filter.py` - Filter automations by criteria
- `ha-remote-restart.py` - Remotely restart Home Assistant

### Kopia

- `kopia-check-backups.py` - Check backup health across Kopia instances

### macOS

- `export-contacts.py` - Export macOS Contacts to CSV
- `MacOS Mount SMB.scpt` - AppleScript for automating SMB share mounts

### MQTT

- `list-devices.py` - List devices seen on MQTT broker
- `mqtt_test.py` - Basic MQTT publish/subscribe testing

### Network

- `network-scan.py` - Scan network and analyze discovered hosts

### OpenSearch

- `opensearch-field-count.py` - Report field counts across indices
- `opensearch-purge-top-queries.py` - Purge top queries data

### Todoist

- `download-backup.py` - Download Todoist backups
- `setup-oauth.py` - Set up Todoist OAuth credentials

### UniFi

- `unifi-api-device-list.py` - List devices from UniFi controller
- `unifi-delete-offline-devices.py` - Remove offline devices from UniFi

### Uptime Kuma

- `uptime-kuma-export.py` - Export monitor configuration
- `uptime-kuma-import.py` - Import monitor configuration
- `uptime-kuma-maintenance.py` - Manage maintenance windows
- `uptime-kuma-enable-notifications.py` - Bulk enable notifications

### Zigbee2MQTT

- `z2m-get-devices.py` - List Zigbee devices
- `z2m-get-color-mode.py` - Query color mode for light devices
- `z2m-monitor-device.py` - Monitor a specific device's MQTT messages

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
