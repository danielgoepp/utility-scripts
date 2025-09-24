#!/usr/bin/env python3

import subprocess
import re
import sys

def get_ipv6_addresses():
    """Extract IPv6 addresses for each network interface."""
    try:
        output = subprocess.check_output(["ifconfig"], encoding="utf-8")
    except subprocess.CalledProcessError as e:
        print(f"Error running ifconfig: {e}", file=sys.stderr)
        sys.exit(1)

    lines = output.split("\n")
    current_interface = ""

    for line in lines:
        interface_match = re.search(r"^(\S+):.*$", line)
        if interface_match:
            current_interface = interface_match.group(1)

        ipv6_match = re.search(r"^\s+inet6 (\S+) .*$", line)
        if ipv6_match and current_interface:
            print(f"{current_interface}: {ipv6_match.group(1)}")

if __name__ == "__main__":
    get_ipv6_addresses()
