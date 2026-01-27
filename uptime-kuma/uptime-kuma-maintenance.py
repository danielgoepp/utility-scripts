"""
ARCHIVED - DO NOT ACTIVELY USE OR MAINTAIN

This script is kept for reference only. The canonical implementation is in the
Ansible repository: ansible/playbooks/ops-maintenance-mode.yaml

The Ansible implementation provides:
- Unified interface for all alert systems (Graylog, Alertmanager, Uptime Kuma)
- AWX/automation workflow integration
- Vault-based credential management
- Full enable/disable functionality with proper cleanup

For maintenance mode operations, use:
    ansible-playbook playbooks/ops-maintenance-mode.yaml -e maintenance_action=enable
    ansible-playbook playbooks/ops-maintenance-mode.yaml -e maintenance_action=disable
"""

import json

from uptime_kuma_api import UptimeKumaApi, MaintenanceStrategy
from config import UPTIME_KUMA_URL, UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD

api = UptimeKumaApi(UPTIME_KUMA_URL)
api.login(UPTIME_KUMA_USERNAME, UPTIME_KUMA_PASSWORD)


def get_monitors():
    monitors = api.get_monitors()
    monitor_names = [monitor["name"] for monitor in monitors]
    # print(monitor_names)
    return monitors


def set_maintenance(monitors):
    create_maintenance_response = api.add_maintenance(
        title="Upgrade Maintenance",
        strategy=MaintenanceStrategy.MANUAL,
        active=True,
    )
    # print(f"Add Maintenance: {response}")
    monitors = [{"id": monitor["id"]} for monitor in monitors]
    # print(f"Monitors: {monitors}")
    response = api.add_monitor_maintenance(
        create_maintenance_response["maintenanceID"], monitors
    )
    print(f"Add monitor maintenance: {response}")


if __name__ == "__main__":
    monitors = get_monitors()

    # file = open("uptime-kuma-maintenance.log", "w")
    # print(json.dump(monitors, file, indent=2))
    # file.close()

    for monitor in monitors:
        print(
            f"{monitor['type']},{monitor['name']},{monitor['hostname']},{monitor['url']},{monitor['method']},{monitor['dns_resolve_server']}"
        )

    print(f"Total monitors: {len(monitors)}")
    # set_maintenance(monitors)
    api.disconnect()
