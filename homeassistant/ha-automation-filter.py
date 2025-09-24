import yaml
import os
from typing import List, Dict, Any


def find_automations_by_label(config_dir: str, label: str) -> List[Dict[Any, Any]]:
    """
    Find all Home Assistant automations with a specific label.

    Args:
        config_dir (str): Path to Home Assistant configuration directory
        label (str): Label to search for in automations

    Returns:
        List[Dict]: List of matching automation configurations
    """
    matching_automations = []

    # Common paths where automation files might be stored
    automation_paths = [
        os.path.join(config_dir, "automations.yaml"),
        os.path.join(config_dir, "configurations/automations.yaml"),
        os.path.join(config_dir, "packages/automations/*.yaml"),
    ]

    def process_automation_file(file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = yaml.safe_load(file)

                # Handle single automation or list of automations
                automations = content if isinstance(content, list) else [content]

                for automation in automations:
                    # Skip if not an automation
                    if not isinstance(automation, dict):
                        continue

                    # Check various places where labels might be stored
                    labels = []

                    # Check in metadata
                    metadata = automation.get("metadata", {})
                    labels.extend(metadata.get("labels", []))

                    # Check in description field
                    description = automation.get("description", "")
                    if description and "#" in description:
                        # Extract hashtag labels from description
                        labels.extend(
                            tag.strip()
                            for tag in description.split()
                            if tag.startswith("#")
                        )

                    # Convert all labels to lowercase for case-insensitive matching
                    labels = [l.lower().replace("#", "") for l in labels]

                    if label.lower() in labels:
                        # Add file path to automation for reference
                        automation["_source_file"] = file_path
                        matching_automations.append(automation)

        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

    # Process each automation file
    for path in automation_paths:
        if "*" in path:
            # Handle glob patterns
            import glob

            for file_path in glob.glob(path):
                process_automation_file(file_path)
        elif os.path.exists(path):
            process_automation_file(path)

    return matching_automations


def print_automation_summary(automations: List[Dict[Any, Any]]) -> None:
    """
    Print a readable summary of found automations.

    Args:
        automations (List[Dict]): List of automation configurations to summarize
    """
    print(f"\nFound {len(automations)} matching automations:\n")

    for idx, automation in enumerate(automations, 1):
        print(f"{idx}. {automation.get('alias', 'Unnamed Automation')}")
        print(f"   Source: {automation.get('_source_file', 'Unknown')}")
        print(f"   Description: {automation.get('description', 'No description')}")
        print(
            f"   Trigger type: {automation.get('trigger', [{}])[0].get('platform', 'Unknown')}"
        )
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Find Home Assistant automations with specific labels"
    )
    parser.add_argument("config_dir", help="Path to Home Assistant config directory")
    parser.add_argument("label", help="Label to search for")
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    automations = find_automations_by_label(args.config_dir, args.label)

    if args.json:
        import json

        print(json.dumps(automations, indent=2))
    else:
        print_automation_summary(automations)


if __name__ == "__main__":
    main()
