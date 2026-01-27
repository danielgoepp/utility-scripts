# Utility Scripts

A collection of Python utility scripts for managing and maintaining various monitoring and infrastructure services.

## Maintenance Mode (ARCHIVED)

**The maintenance mode scripts in this repository are archived and kept for reference only.**

The canonical implementation for maintenance mode is in the Ansible repository:

```bash
# Enable maintenance mode (mutes all alerts)
ansible-playbook playbooks/ops-maintenance-mode.yaml -e maintenance_action=enable

# Disable maintenance mode (unmutes all alerts)
ansible-playbook playbooks/ops-maintenance-mode.yaml -e maintenance_action=disable

# Target specific systems
ansible-playbook playbooks/ops-maintenance-mode.yaml -e maintenance_action=enable -e target=graylog
```

The Ansible implementation provides a unified interface for all alert systems, AWX integration, and vault-based credential management.

## Services

- **Cloudflare** - DNS and certificate management utilities
- **Home Assistant** - Smart home platform integration utilities
- **Uptime Kuma** - Export/import utilities (maintenance scripts archived)

## Quick Start

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   # Copy example files and edit with your values
   cp cloudflare/.env.example cloudflare/.env
   cp homeassistant/.env.example homeassistant/.env
   cp uptime-kuma/.env.example uptime-kuma/.env
   ```

3. **Run scripts:**
   ```bash
   # Examples
   python3 cloudflare/cf_clear_stale_acme.py
   python3 uptime-kuma/uptime-kuma-export.py
   ```

## Architecture

Each service directory follows a consistent pattern:

```text
service/
├── config.py          # Environment variable configuration
├── service-script.py  # Main functionality
├── .env              # Your environment variables (gitignored)
└── .env.example      # Template for required variables
```

All scripts use centralized configuration management with `python-dotenv` for secure credential handling.

## Available Scripts

### Cloudflare
- `cf_clear_stale_acme.py` - Clean up stale ACME challenge records

### Uptime Kuma
- `uptime-kuma-export.py` - Export monitor configuration
- `uptime-kuma-import.py` - Import monitor configuration

### Archived (Reference Only)

The following maintenance scripts are archived. Use the Ansible playbook instead:

- `alertmanager/alertmanager-maintenance.py`
- `graylog/graylog-maintenance.py`
- `uptime-kuma/uptime-kuma-maintenance.py`

## Usage Examples

```bash
# Clean Cloudflare ACME records
python3 cloudflare/cf_clear_stale_acme.py

# Export Uptime Kuma monitors
python3 uptime-kuma/uptime-kuma-export.py

# Import Uptime Kuma monitors
python3 uptime-kuma/uptime-kuma-import.py
```

Use `--help` with any script for detailed usage information.
