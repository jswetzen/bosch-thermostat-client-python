#!/usr/bin/env python3
"""Interactive Terminal UI for PoinTT API Testing

Allows manual testing of all PoinTT API entities with live state display.
Perfect for comparing behavior with the official app.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from bosch_thermostat_client.const import POINTTAPI, AC
from bosch_thermostat_client.gateway import gateway_chooser

# Terminal colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Configuration
DEVICE_ID = "101638933"
TOKENS_FILE = "tokens.json"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}{text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}{text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}{text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}{text}{Colors.ENDC}")


def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


async def fetch_all_states(gateway):
    """Fetch all current states from the API."""
    try:
        # Get the bulk endpoint data
        result = await gateway._connector.get("/airConditioning/standardFunctions")

        entities = []
        if result and 'references' in result:
            for ref in result['references']:
                entity = {
                    'id': ref.get('id', ''),
                    'name': ref.get('id', '').split('/')[-1],
                    'type': ref.get('type', ''),
                    'value': ref.get('value', ''),
                    'writeable': ref.get('writeable', 0),
                    'allowed_values': ref.get('allowedValues', []),
                    'min': ref.get('minValue'),
                    'max': ref.get('maxValue'),
                    'unit': ref.get('unitOfMeasure', ''),
                }
                entities.append(entity)

        return entities
    except Exception as e:
        print_error(f"Error fetching states: {e}")
        return []


def display_entities(entities):
    """Display all entities in a nice table format."""
    print(f"\n{Colors.BOLD}Current States:{Colors.ENDC}")
    print(f"{Colors.BOLD}{'#':<4} {'Name':<25} {'Value':<20} {'Writable':<10}{Colors.ENDC}")
    print("-" * 70)

    for idx, entity in enumerate(entities, 1):
        name = entity['name']
        value = str(entity['value'])

        # Format value with unit
        if entity['unit']:
            value = f"{value} {entity['unit']}"

        # Color code based on writeability
        if entity['writeable']:
            writable_str = f"{Colors.OKGREEN}YES{Colors.ENDC}"
            name_str = f"{Colors.BOLD}{name}{Colors.ENDC}"
        else:
            writable_str = f"{Colors.WARNING}NO{Colors.ENDC}"
            name_str = name

        print(f"{idx:<4} {name_str:<25} {value:<20} {writable_str:<10}")

    print("-" * 70)


def display_entity_details(entity):
    """Display detailed information about an entity."""
    print(f"\n{Colors.BOLD}Entity Details:{Colors.ENDC}")
    print(f"  Name: {Colors.BOLD}{entity['name']}{Colors.ENDC}")
    print(f"  ID: {entity['id']}")
    print(f"  Type: {entity['type']}")
    print(f"  Current Value: {Colors.OKGREEN}{entity['value']}{Colors.ENDC}", end="")
    if entity['unit']:
        print(f" {entity['unit']}")
    else:
        print()
    print(f"  Writable: {'Yes' if entity['writeable'] else 'No'}")

    if entity['allowed_values']:
        print(f"  Allowed Values: {', '.join(map(str, entity['allowed_values']))}")

    if entity['min'] is not None and entity['max'] is not None:
        print(f"  Range: {entity['min']} - {entity['max']}")


def get_user_input(prompt, allowed_values=None):
    """Get user input with optional validation."""
    while True:
        try:
            value = input(f"\n{prompt}: ").strip()

            if value.lower() == 'q':
                return None

            if allowed_values:
                if value in allowed_values:
                    return value
                else:
                    print_error(f"Invalid value. Must be one of: {', '.join(allowed_values)}")
                    continue

            return value
        except KeyboardInterrupt:
            return None


async def set_entity_value(gateway, entity, new_value):
    """Set a new value for an entity."""
    entity_id = entity['id']
    entity_type = entity['type']

    # Convert value to appropriate type
    try:
        if entity_type == 'floatValue':
            new_value = float(new_value)
        elif entity_type == 'intValue':
            new_value = int(new_value)
        # stringValue stays as string
    except ValueError:
        print_error(f"Invalid value type for {entity_type}")
        return False

    print_info(f"Setting {entity['name']} to {new_value}...")

    try:
        await gateway._connector.put(entity_id, new_value)
        print_success("✓ Write request sent successfully")

        # Wait a moment and read back
        await asyncio.sleep(1)
        result = await gateway._connector.get(entity_id)
        actual_value = result.get('value')

        print_info(f"Reading back current value: {actual_value}")

        if str(actual_value) == str(new_value):
            print_success("✓ Value confirmed!")
            return True
        else:
            print_warning(f"⚠ Value mismatch: expected {new_value}, got {actual_value}")
            print_warning("The device may have rejected the change due to current state/mode")
            return False

    except Exception as e:
        print_error(f"✗ Error: {e}")
        return False


async def interactive_loop(gateway):
    """Main interactive loop."""
    while True:
        try:
            # Fetch current states
            print_info("Fetching current states...")
            entities = await fetch_all_states(gateway)

            if not entities:
                print_error("No entities found!")
                return

            # Display entities
            clear_screen()
            print_header("PoinTT API Interactive Testing")
            print_info(f"Device ID: {DEVICE_ID}")
            print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            display_entities(entities)

            # Menu
            print(f"\n{Colors.BOLD}Options:{Colors.ENDC}")
            print("  • Enter number (1-{}) to modify an entity".format(len(entities)))
            print("  • Press 'r' to refresh")
            print("  • Press 'q' to quit")

            choice = input(f"\n{Colors.BOLD}Your choice: {Colors.ENDC}").strip().lower()

            if choice == 'q':
                print_info("\nGoodbye!")
                break

            if choice == 'r':
                continue

            # Try to parse as number
            try:
                idx = int(choice)
                if 1 <= idx <= len(entities):
                    entity = entities[idx - 1]

                    # Check if writable
                    if not entity['writeable']:
                        print_error("\n✗ This entity is read-only!")
                        input("\nPress Enter to continue...")
                        continue

                    # Show details
                    display_entity_details(entity)

                    # Get new value
                    if entity['allowed_values']:
                        print(f"\n{Colors.BOLD}Allowed values:{Colors.ENDC}")
                        for i, val in enumerate(entity['allowed_values'], 1):
                            print(f"  {i}. {val}")

                        value_choice = get_user_input("Enter value or number", entity['allowed_values'])

                        if value_choice is None:
                            continue

                        # Check if it's a number referring to position
                        try:
                            val_idx = int(value_choice)
                            if 1 <= val_idx <= len(entity['allowed_values']):
                                new_value = entity['allowed_values'][val_idx - 1]
                            else:
                                new_value = value_choice
                        except ValueError:
                            new_value = value_choice
                    else:
                        prompt = "Enter new value (q to cancel)"
                        if entity['min'] is not None and entity['max'] is not None:
                            prompt += f" [{entity['min']}-{entity['max']}]"

                        new_value = get_user_input(prompt)

                        if new_value is None:
                            continue

                        # Validate range
                        if entity['min'] is not None and entity['max'] is not None:
                            try:
                                num_val = float(new_value)
                                if not (entity['min'] <= num_val <= entity['max']):
                                    print_error(f"Value must be between {entity['min']} and {entity['max']}")
                                    input("\nPress Enter to continue...")
                                    continue
                            except ValueError:
                                print_error("Invalid numeric value")
                                input("\nPress Enter to continue...")
                                continue

                    # Set the value
                    await set_entity_value(gateway, entity, new_value)

                    input("\nPress Enter to continue...")
                else:
                    print_error(f"\n✗ Invalid number. Must be 1-{len(entities)}")
                    input("\nPress Enter to continue...")
            except ValueError:
                print_error("\n✗ Invalid input")
                input("\nPress Enter to continue...")

        except KeyboardInterrupt:
            print_info("\n\nGoodbye!")
            break
        except Exception as e:
            print_error(f"\nUnexpected error: {e}")
            input("\nPress Enter to continue...")


async def main():
    """Main function."""
    print_header("PoinTT API Interactive Testing Tool")

    # Load tokens
    print_info(f"Loading OAuth tokens from {TOKENS_FILE}...")
    try:
        with open(TOKENS_FILE, 'r') as f:
            tokens = json.load(f)
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        print_success(f"✓ Loaded access_token: {access_token[:20]}...")
        print_success(f"✓ Loaded refresh_token: {refresh_token[:20]}...")
    except FileNotFoundError:
        print_error(f"✗ {TOKENS_FILE} not found!")
        print_info("Please create a tokens.json file with your OAuth tokens.")
        return
    except Exception as e:
        print_error(f"✗ Error loading tokens: {e}")
        return

    # Create session
    async with aiohttp.ClientSession() as session:
        # Initialize gateway
        print_info("\nInitializing PoinTT API gateway...")
        try:
            GatewayClass = gateway_chooser(POINTTAPI)
            gateway = GatewayClass(
                session=session,
                session_type="HTTP",
                host=DEVICE_ID,
                access_key=None,
                access_token=access_token,
                refresh_token=refresh_token,
                token_file=TOKENS_FILE
            )

            await gateway.initialize()
            print_success("✓ Gateway initialized")
            print_info(f"  Device type: {gateway.device_type}")
            print_info(f"  Bus type: {gateway.bus_type}")
            print_info(f"  UUID: {gateway.uuid}")

            # Initialize AC circuits
            print_info("\nInitializing AC circuits...")
            await gateway.initialize_circuits(AC)
            circuits = gateway.ac_circuits

            if not circuits:
                print_error("No AC circuits found")
                return

            print_success(f"✓ Found {len(circuits)} AC circuit(s)")
            for circuit in circuits:
                print_info(f"  Circuit ID: {circuit.attr_id}")

            # Start interactive loop
            input("\nPress Enter to start interactive testing...")
            await interactive_loop(gateway)

        except Exception as e:
            print_error(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await gateway.close()


if __name__ == "__main__":
    asyncio.run(main())
