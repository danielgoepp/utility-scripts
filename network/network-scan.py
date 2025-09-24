#!/usr/bin/env python3

import socket
import ipaddress
import argparse
import sys
from scapy.all import srp, Ether, ARP

def get_local_ip():
    """Get the local IP address by connecting to a remote address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception as e:
        print(f"Error getting local IP: {e}", file=sys.stderr)
        sys.exit(1)

def scan_network(network_cidr, timeout=2):
    """Perform ARP scan on the specified network."""
    print(f"Scanning network: {network_cidr}")

    try:
        answered, _ = srp(
            Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=str(network_cidr)),
            timeout=timeout,
            verbose=False
        )
    except Exception as e:
        print(f"Error during network scan: {e}", file=sys.stderr)
        return {}

    arp_table = {}
    for _, received in answered:
        arp_table[received.hwsrc] = received.psrc

    print(f"Found {len(arp_table)} devices")
    return arp_table

def print_scan_results(arp_table):
    """Print the scan results in a formatted table."""
    if not arp_table:
        print("No devices found")
        return

    print("\nDiscovered devices:")
    print(f"{'MAC Address':<18} {'IP Address':<15}")
    print("-" * 35)

    for mac, ip in sorted(arp_table.items(), key=lambda x: ipaddress.IPv4Address(x[1])):
        print(f"{mac:<18} {ip:<15}")

def find_device_by_mac(arp_table, mac_address):
    """Find a specific device by MAC address."""
    if mac_address.lower() in [mac.lower() for mac in arp_table.keys()]:
        for mac, ip in arp_table.items():
            if mac.lower() == mac_address.lower():
                return ip
    return None

def main():
    parser = argparse.ArgumentParser(description="Network ARP scanner")
    parser.add_argument("--network", "-n", help="Network CIDR (e.g., 192.168.1.0/24)")
    parser.add_argument("--mac", "-m", help="Find IP address for specific MAC address")
    parser.add_argument("--timeout", "-t", type=int, default=2, help="Scan timeout in seconds")

    args = parser.parse_args()

    if args.network:
        try:
            network = ipaddress.IPv4Network(args.network, strict=False)
        except ValueError as e:
            print(f"Invalid network: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        local_ip = get_local_ip()
        print(f"Local IP: {local_ip}")
        interface = ipaddress.IPv4Interface(f"{local_ip}/24")
        network = interface.network
        print(f"Network: {network}")

    arp_table = scan_network(network, args.timeout)

    if args.mac:
        ip = find_device_by_mac(arp_table, args.mac)
        if ip:
            print(f"Device {args.mac} found at IP: {ip}")
        else:
            print(f"Device {args.mac} not found")
    else:
        print_scan_results(arp_table)

if __name__ == "__main__":
    main()
