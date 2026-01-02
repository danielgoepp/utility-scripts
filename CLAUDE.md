# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This repository contains a collection of Python utility scripts for managing and maintaining various monitoring and infrastructure services. The codebase is organized into service-specific directories:

- **alertmanager/**: Scripts for managing Prometheus AlertManager silences and maintenance windows
- **cloudflare/**: Utilities for Cloudflare DNS and certificate management
- **graylog/**: Scripts for Graylog log management system maintenance
- **hertzbeat/**: Tools for HertzBeat monitoring system management
- **homeassistant/**: Utilities for Home Assistant smart home platform integration
- **jira/**: JIRA project management and issue tracking utilities
- **mqtt/**: MQTT client utilities for messaging and testing
- **network/**: Network scanning and analysis tools
- **unifi/**: UniFi network controller management utilities
- **uptime-kuma/**: Utilities for Uptime Kuma monitoring service
- **zigbee2mqtt/**: Zigbee device monitoring and management via MQTT

Each service directory follows a consistent pattern:

- `config.py`: Centralized configuration management using environment variables loaded via `python-dotenv`
- `*-maintenance.py`: Main script for service maintenance operations
- `.env`: Environment variables file (gitignored)
- `.env.example`: Template showing required environment variables

## Configuration Pattern

All scripts use a standardized configuration approach:

- Environment variables stored in `.env` files for sensitive data (API tokens, URLs, credentials)
- Centralized `config.py` files that load environment variables using `python-dotenv`
- Scripts import configuration values from their respective `config.py` files
- `.env.example` files provided as templates showing all required environment variables
- No hardcoded credentials or URLs in the scripts

Example `config.py` structure:

```python
import os
from dotenv import load_dotenv

load_dotenv()

SERVICE_URL = os.getenv("SERVICE_URL")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN")
```

## Script Execution

All Python scripts are designed to be run directly. **Always activate the virtual environment first:**

```bash
source .venv/bin/activate
python3 <service>/<script-name>.py
```

Most scripts include command-line argument parsing and can be run with `-h` for help.

## Dependencies

Install dependencies into the virtual environment:

```bash
source .venv/bin/activate
pip3 install -r requirements.txt
```

Scripts use external Python libraries:

- `requests` for HTTP API calls
- `uptime-kuma-api` for Uptime Kuma integration
- `pandas` for data processing (hertzbeat-management.py)
- `python-dotenv` for environment variable loading
- `paho-mqtt` for MQTT client operations
- `scapy` for network packet manipulation and analysis
- Standard library modules: `os`, `json`, `argparse`, `datetime`, `smtplib`

## File Naming Convention

All Python scripts follow dash-separated naming for consistency:

- `device-management.py` (not `device_management.py`)
- `get-entities.py` (not `get_entities.py`)
- `unifi-delete-offline-devices.py` (not `unifi_delete_offline_devices.py`)

## Common Operations

- **Maintenance Mode**: Scripts typically provide functionality to enable/disable maintenance windows
- **API Integration**: All scripts interact with their respective service APIs
- **Network Operations**: Network scanning, device discovery, and packet analysis
- **Device Management**: Monitor and manage IoT devices, network equipment, and smart home systems
- **Monitoring & Alerting**: Real-time monitoring with email notifications and status reporting
- **Logging**: Scripts output operational information and status updates
- **Error Handling**: Scripts include comprehensive error handling for all operations