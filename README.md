# Utility Scripts

A collection of Python utility scripts for managing and maintaining various monitoring and infrastructure services.

## Services

- **AlertManager** - Prometheus AlertManager silence management
- **Cloudflare** - DNS and certificate management utilities
- **Graylog** - Log management system maintenance
- **HertzBeat** - Monitoring system management tools
- **Uptime Kuma** - Uptime monitoring service utilities

## Quick Start

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   # Copy example files and edit with your values
   cp alertmanager/.env.example alertmanager/.env
   cp cloudflare/.env.example cloudflare/.env
   cp graylog/.env.example graylog/.env
   cp hertzbeat/.env.example hertzbeat/.env
   cp uptime-kuma/.env.example uptime-kuma/.env
   ```

3. **Run scripts:**
   ```bash
   # Examples
   python3 alertmanager/alertmanager-maintenance.py --mute --duration 4
   python3 graylog/graylog-maintenance.py --mute
   python3 hertzbeat/hertzbeat-maintenance.py --list
   ```

## Architecture

Each service directory follows a consistent pattern:

```
service/
├── config.py          # Environment variable configuration
├── service-script.py  # Main functionality
├── .env              # Your environment variables (gitignored)
└── .env.example      # Template for required variables
```

All scripts use centralized configuration management with `python-dotenv` for secure credential handling.

## Available Scripts

### AlertManager
- `alertmanager-maintenance.py` - Create/remove maintenance silences

### Cloudflare
- `cf_clear_stale_acme.py` - Clean up stale ACME challenge records

### Graylog
- `graylog-maintenance.py` - Mute/unmute event definitions

### HertzBeat
- `hertzbeat-maintenance.py` - Manage alert silences
- `hertzbeat-management.py` - Monitor management utilities

### Uptime Kuma
- `uptime-kuma-maintenance.py` - Maintenance window management

## Usage Examples

```bash
# Mute alerts for 2 hours (default)
python3 alertmanager/alertmanager-maintenance.py --mute

# Mute alerts for 4 hours
python3 alertmanager/alertmanager-maintenance.py --mute --duration 4

# Remove all silences
python3 alertmanager/alertmanager-maintenance.py --unmute

# List HertzBeat silences
python3 hertzbeat/hertzbeat-maintenance.py --list

# Clean Cloudflare ACME records
python3 cloudflare/cf_clear_stale_acme.py
```

Use `--help` with any script for detailed usage information.