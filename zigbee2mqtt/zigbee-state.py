#!/usr/bin/env python3

import json
import sys
import argparse
import config


def read_state_file(file_path):
    """Read and parse the zigbee state JSON file."""
    try:
        with open(file_path, 'r') as state_file:
            return json.load(state_file)
    except FileNotFoundError:
        print(f"Error: State file not found at {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in state file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        sys.exit(1)


def process_device_states(state_data):
    """Process device state data and output in specified format."""
    results = []

    for device_name, device_data in state_data.items():
        if not isinstance(device_data, dict):
            continue

        color_mode = device_data.get('color_mode')

        if color_mode == 'xy':
            color = device_data.get('color', {})
            x_coord = color.get('x')
            y_coord = color.get('y')
            if x_coord is not None and y_coord is not None:
                results.append({
                    'device': device_name,
                    'mode': 'xy',
                    'value': f"[{x_coord},{y_coord}]"
                })
        elif color_mode == 'color_temp':
            color_temp = device_data.get('color_temp')
            if color_temp is not None:
                results.append({
                    'device': device_name,
                    'mode': 'color_temp',
                    'value': str(color_temp)
                })
        else:
            results.append({
                'device': device_name,
                'mode': color_mode or 'unknown',
                'value': 'N/A'
            })

    return results


def print_results(results, output_format='table'):
    """Print results in specified format."""
    if output_format == 'csv':
        print("Device,Mode,Value")
        for result in results:
            print(f"{result['device']},{result['mode']},{result['value']}")
    elif output_format == 'json':
        print(json.dumps(results, indent=2))
    else:  # table format
        if not results:
            print("No device states found.")
            return

        print(f"{'Device':<30} {'Mode':<15} {'Value':<20}")
        print("-" * 65)
        for result in results:
            print(f"{result['device']:<30} {result['mode']:<15} {result['value']:<20}")


def main():
    """Main function to process zigbee device states."""
    parser = argparse.ArgumentParser(description="Process Zigbee device state information")
    parser.add_argument("--file", "-f", default=config.STATE_FILE_PATH,
                       help=f"Path to state JSON file (default: {config.STATE_FILE_PATH})")
    parser.add_argument("--format", "-o", choices=['table', 'csv', 'json'],
                       default='table', help="Output format")
    parser.add_argument("--filter", help="Filter devices by name (case insensitive)")

    args = parser.parse_args()

    try:
        state_data = read_state_file(args.file)

        # Apply name filter if specified
        if args.filter:
            filtered_data = {k: v for k, v in state_data.items()
                           if args.filter.lower() in k.lower()}
            state_data = filtered_data

        results = process_device_states(state_data)
        print_results(results, args.format)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()