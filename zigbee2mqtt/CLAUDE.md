# Zigbee2MQTT Utilities

This directory contains Python scripts for monitoring and managing Zigbee devices via Zigbee2MQTT and MQTT.

## Scripts

### z2m-get-devices.py

Collects and displays Zigbee device information from the Zigbee2MQTT bridge via MQTT.

**Features:**
- Connects to MQTT broker and subscribes to `zigbee15/bridge/info` topic
- Retrieves device configuration including device ID, friendly name, type, and model
- Supports multiple output formats: table, CSV, JSON
- Optional detailed view showing all device properties
- Device name filtering (case insensitive)

**Usage:**
```bash
python3 z2m-get-devices.py [--format table|csv|json] [--details] [--timeout SECONDS] [--filter NAME]
```

### z2m-get-offline.py

Monitors Zigbee devices for offline status and optionally sends email notifications.

**Features:**
- Scans multiple Zigbee2MQTT bridges (zigbee11, zigbee15) for offline devices
- Subscribes to `+/availability` topics to detect device status
- Email notification support when offline devices are found
- Multiple output formats: table, CSV, JSON
- Quiet mode for scripting/automation
- Returns exit code 1 if offline devices are found (useful for monitoring)

**Usage:**
```bash
python3 z2m-get-offline.py [--email] [--format table|csv|json] [--timeout SECONDS] [--quiet]
```

### zigbee-state.py

Processes Zigbee device state information from a JSON state file, focusing on color mode and color values.

**Features:**
- Reads device state from a JSON file (default: `/tmp/state.json`)
- Extracts color mode information (xy coordinates or color temperature)
- Supports multiple output formats: table, CSV, JSON
- Device name filtering (case insensitive)

**Usage:**
```bash
python3 zigbee-state.py [--file PATH] [--format table|csv|json] [--filter NAME]
```

## Configuration

All scripts use shared configuration from `config.py` which loads environment variables from `.env`.

### Required Environment Variables

```bash
# MQTT Configuration
MQTT_HOST=your_mqtt_host
MQTT_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password

# Email Configuration (for z2m-get-offline.py)
SMTP_HOST=your_smtp_host
SMTP_PORT=587
FROM_EMAIL=sender@example.com
TO_EMAIL=recipient@example.com

# File paths (for zigbee-state.py)
STATE_FILE_PATH=/tmp/state.json
```

Copy `.env.example` to `.env` and fill in your values.

## Dependencies

- `paho-mqtt`: MQTT client library
- `python-dotenv`: Environment variable loading
- Standard library: `json`, `argparse`, `smtplib`, `email`
