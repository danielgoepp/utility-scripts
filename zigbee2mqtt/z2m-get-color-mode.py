#!/usr/bin/env python3

import json
import sys
import argparse
import os
import yaml
import config



def read_state_file(file_path):
    """Read and parse the zigbee state JSON file."""
    try:
        with open(file_path, 'r') as state_file:
            return json.load(state_file)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in state file {file_path}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading state file {file_path}: {e}", file=sys.stderr)
        return None


def read_config_file(file_path):
    """Read and parse the zigbee2mqtt configuration YAML file."""
    try:
        with open(file_path, 'r') as config_file:
            return yaml.safe_load(config_file)
    except FileNotFoundError:
        return None
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in config file {file_path}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading config file {file_path}: {e}", file=sys.stderr)
        return None


def get_friendly_names(base_path, instances):
    """Read friendly names from all configuration files."""
    friendly_names = {}

    for instance in instances:
        config_file = os.path.join(base_path, instance, "configuration.yaml")
        config_data = read_config_file(config_file)
        if config_data and 'devices' in config_data:
            for device_id, device_info in config_data['devices'].items():
                if isinstance(device_info, dict) and 'friendly_name' in device_info:
                    key = f"[{instance}] {device_id}"
                    friendly_names[key] = device_info['friendly_name']

    return friendly_names


def read_all_state_files(base_path, instances):
    """Read state files from all zigbee2mqtt instances."""
    all_state_data = {}

    for instance in instances:
        state_file = os.path.join(base_path, instance, "state.json")
        state_data = read_state_file(state_file)
        if state_data:
            # Prefix device names with instance to avoid collisions
            for device_name, device_data in state_data.items():
                prefixed_name = f"[{instance}] {device_name}"
                all_state_data[prefixed_name] = device_data

    if not all_state_data:
        print(f"Error: No state files found in {base_path}", file=sys.stderr)
        sys.exit(1)

    return all_state_data


def process_device_states(state_data, friendly_names=None):
    """Process device state data and output in specified format."""
    results = []
    friendly_names = friendly_names or {}

    for device_name, device_data in state_data.items():
        if not isinstance(device_data, dict):
            continue

        color_mode = device_data.get('color_mode')
        if not color_mode:
            continue

        friendly_name = friendly_names.get(device_name, '')

        if color_mode == 'xy':
            color = device_data.get('color', {})
            x_coord = color.get('x')
            y_coord = color.get('y')
            if x_coord is not None and y_coord is not None:
                results.append({
                    'device': device_name,
                    'friendly_name': friendly_name,
                    'mode': 'xy',
                    'value': f"[{x_coord},{y_coord}]"
                })
        elif color_mode == 'color_temp':
            color_temp = device_data.get('color_temp')
            if color_temp is not None:
                results.append({
                    'device': device_name,
                    'friendly_name': friendly_name,
                    'mode': 'color_temp',
                    'value': str(color_temp)
                })

    return results


def print_results(results, output_format='table'):
    """Print results in specified format."""
    if output_format == 'csv':
        print("Device,Friendly Name,Mode,Value")
        for result in results:
            print(f"{result['device']},{result['friendly_name']},{result['mode']},{result['value']}")
    elif output_format == 'json':
        print(json.dumps(results, indent=2))
    else:  # table format
        if not results:
            print("No device states found.")
            return

        print(f"{'Device':<26} {'Friendly Name':<28} {'Mode':<12} {'Value':<20}")
        print("-" * 86)
        for result in results:
            friendly = result['friendly_name'][:26] if result['friendly_name'] else ''
            print(f"{result['device']:<26} {friendly:<28} {result['mode']:<12} {result['value']:<20}")


def main():
    """Main function to process zigbee device states."""
    parser = argparse.ArgumentParser(description="Process Zigbee device state information")
    parser.add_argument("--file", "-f",
                       help="Path to a single state JSON file (overrides default directory scan)")
    parser.add_argument("--base-path", "-b", default=config.Z2M_BASE_PATH,
                       help=f"Base path for zigbee2mqtt data (default: {config.Z2M_BASE_PATH})")
    parser.add_argument("--instances", "-i", nargs="+", default=config.Z2M_INSTANCES,
                       help=f"Instance directories to scan (default: {' '.join(config.Z2M_INSTANCES)})")
    parser.add_argument("--format", "-o", choices=['table', 'csv', 'json'],
                       default='table', help="Output format")
    parser.add_argument("--filter", help="Filter devices by name (case insensitive)")

    args = parser.parse_args()

    try:
        if args.file:
            # Use single file mode if --file is specified
            state_data = read_state_file(args.file)
            if state_data is None:
                print(f"Error: Could not read state file {args.file}", file=sys.stderr)
                sys.exit(1)
            friendly_names = {}
        else:
            # Read from all instance directories
            state_data = read_all_state_files(args.base_path, args.instances)
            friendly_names = get_friendly_names(args.base_path, args.instances)

        # Apply name filter if specified (searches both device ID and friendly name)
        if args.filter:
            filter_lower = args.filter.lower()
            filtered_data = {k: v for k, v in state_data.items()
                           if filter_lower in k.lower() or
                              filter_lower in friendly_names.get(k, '').lower()}
            state_data = filtered_data

        results = process_device_states(state_data, friendly_names)
        print_results(results, args.format)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()