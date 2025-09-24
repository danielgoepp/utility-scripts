#!/usr/bin/env python3

import requests
import json
import config
import csv
import argparse
from datetime import datetime

def get_color_values(attributes, color_mode):
    """Extract color values based on the current color mode"""
    color_values = {}
    
    if color_mode == "rgb":
        color_values["rgb_color"] = attributes.get("rgb_color", [])
    elif color_mode == "xy":
        color_values["xy_color"] = attributes.get("xy_color", [])
    elif color_mode == "hs":
        color_values["hs_color"] = attributes.get("hs_color", [])
    elif color_mode == "color_temp":
        color_values["color_temp"] = attributes.get("color_temp")
        color_values["color_temp_kelvin"] = attributes.get("color_temp_kelvin")
    elif color_mode == "brightness":
        # Only brightness, no color
        pass
    elif color_mode == "onoff":
        # Only on/off, no brightness or color
        pass
    
    return color_values

def format_color_value(light_info):
    """Format the color value based on color mode for display"""
    color_mode = light_info.get("color_mode")
    if not color_mode or color_mode in ["brightness", "onoff"]:
        return "-"
    
    if color_mode == "rgb" and "rgb_color" in light_info:
        rgb = light_info["rgb_color"]
        return f"RGB({rgb[0]},{rgb[1]},{rgb[2]})"
    elif color_mode == "xy" and "xy_color" in light_info:
        xy = light_info["xy_color"]
        return f"XY({xy[0]:.3f},{xy[1]:.3f})"
    elif color_mode == "hs" and "hs_color" in light_info:
        hs = light_info["hs_color"]
        return f"HS({hs[0]:.1f},{hs[1]:.1f})"
    elif color_mode == "color_temp" and "color_temp" in light_info:
        temp = light_info["color_temp"]
        kelvin = light_info.get("color_temp_kelvin", "")
        if kelvin:
            return f"{temp}K ({kelvin})"
        return f"{temp}K"
    
    return "-"

def print_table(light_settings):
    """Print lights in a formatted table with dynamic column widths"""
    # Calculate maximum widths needed
    max_entity_id = max(len("Entity ID"), max(len(light["entity_id"]) for light in light_settings))
    max_name = max(len("Name"), max(len(light["friendly_name"]) for light in light_settings))
    max_state = max(len("State"), max(len(light["state"]) for light in light_settings))
    max_brightness = max(len("Brightness"), max(len(str(light["brightness"]) if light["brightness"] is not None else "-") for light in light_settings))
    max_color_mode = max(len("Color Mode"), max(len(light["color_mode"] if light["color_mode"] else "-") for light in light_settings))
    max_color_value = max(len("Color Value"), max(len(format_color_value(light)) for light in light_settings))
    
    # Add some padding
    max_entity_id += 2
    max_name += 2
    max_state += 2
    max_brightness += 2
    max_color_mode += 2
    max_color_value += 2
    
    # Print header
    total_width = max_entity_id + max_name + max_state + max_brightness + max_color_mode + max_color_value
    print(f"\n{'Entity ID':<{max_entity_id}} {'Name':<{max_name}} {'State':<{max_state}} {'Brightness':<{max_brightness}} {'Color Mode':<{max_color_mode}} {'Color Value':<{max_color_value}}")
    print("-" * total_width)
    
    # Print data rows
    for light in light_settings:
        entity_id = light["entity_id"]
        name = light["friendly_name"]
        state = light["state"]
        brightness = str(light["brightness"]) if light["brightness"] is not None else "-"
        color_mode = light["color_mode"] if light["color_mode"] else "-"
        color_value = format_color_value(light)
        
        print(f"{entity_id:<{max_entity_id}} {name:<{max_name}} {state:<{max_state}} {brightness:<{max_brightness}} {color_mode:<{max_color_mode}} {color_value:<{max_color_value}}")

def save_csv(light_settings, filename):
    """Save lights to CSV file"""
    fieldnames = ['entity_id', 'friendly_name', 'state', 'brightness', 'color_mode', 
                  'color_value', 'supported_color_modes', 'manufacturer', 'model']
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for light in light_settings:
            row = {
                'entity_id': light['entity_id'],
                'friendly_name': light['friendly_name'],
                'state': light['state'],
                'brightness': light.get('brightness', ''),
                'color_mode': light.get('color_mode', ''),
                'color_value': format_color_value(light),
                'supported_color_modes': ','.join(light.get('supported_color_modes', [])),
                'manufacturer': light.get('manufacturer', ''),
                'model': light.get('model', '')
            }
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description='Extract Home Assistant light settings')
    parser.add_argument('--format', choices=['table', 'csv'], default='table', 
                        help='Output format: table (default) or csv')
    parser.add_argument('--save', action='store_true', 
                        help='Save CSV to file (only applies when format is csv)')
    
    args = parser.parse_args()
    
    headers = {
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.get(f"https://{config.HOST}/api/states", headers=headers)

    if response.status_code == 200:
        entities = response.json()
        light_settings = []

        for entity in entities:
            if entity['entity_id'].startswith('light.'):
                attributes = entity['attributes']
                
                light_info = {
                    "entity_id": entity['entity_id'],
                    "friendly_name": attributes.get("friendly_name", entity['entity_id']),
                    "state": entity['state'],
                    "brightness": attributes.get("brightness"),
                    "color_mode": attributes.get("color_mode"),
                    "supported_color_modes": attributes.get("supported_color_modes", []),
                }
                
                # Add color values based on current color mode
                if light_info["color_mode"]:
                    color_values = get_color_values(attributes, light_info["color_mode"])
                    light_info.update(color_values)
                
                # Additional useful attributes
                if "device_class" in attributes:
                    light_info["device_class"] = attributes["device_class"]
                if "model" in attributes:
                    light_info["model"] = attributes["model"]
                if "manufacturer" in attributes:
                    light_info["manufacturer"] = attributes["manufacturer"]
                
                light_settings.append(light_info)

        print(f"Found {len(light_settings)} light entities")
        
        if args.format == 'table':
            print_table(light_settings)
        elif args.format == 'csv':
            if args.save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"light_settings_{timestamp}.csv"
                save_csv(light_settings, filename)
                print(f"Light settings saved to {filename}")
            else:
                # Print CSV to stdout
                import io
                output = io.StringIO()
                fieldnames = ['entity_id', 'friendly_name', 'state', 'brightness', 'color_mode', 
                              'color_value', 'supported_color_modes', 'manufacturer', 'model']
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for light in light_settings:
                    row = {
                        'entity_id': light['entity_id'],
                        'friendly_name': light['friendly_name'],
                        'state': light['state'],
                        'brightness': light.get('brightness', ''),
                        'color_mode': light.get('color_mode', ''),
                        'color_value': format_color_value(light),
                        'supported_color_modes': ','.join(light.get('supported_color_modes', [])),
                        'manufacturer': light.get('manufacturer', ''),
                        'model': light.get('model', '')
                    }
                    writer.writerow(row)
                
                print(output.getvalue())

    else:
        print(f"Failed to retrieve entities, status code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()