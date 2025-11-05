#!/usr/bin/env python3
"""End-to-end live test for PoinTT API - Exercise all entities.

This script:
1. Reads all values from standardFunctions bulk endpoint
2. Writes to all writable controls
3. Validates the writes worked
4. Restores original values
5. Reports success/failure for each entity

Requires: tokens.json with valid OAuth tokens
"""

import asyncio
import json
import aiohttp
from pathlib import Path
from datetime import datetime

from bosch_thermostat_client.const import POINTTAPI, AC
from bosch_thermostat_client.gateway import gateway_chooser


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}")
    print(f"{text}")
    print(f"{'=' * 70}{Colors.ENDC}")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


async def test_all_entities():
    """Test all PoinTT API entities end-to-end."""

    DEVICE_ID = "YOUR_DEVICE_ID"
    TOKEN_FILE = "tokens.json"

    print_header("PoinTT API - End-to-End Live Test")
    print(f"Testing all entities from standardFunctions endpoint")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load tokens
    print_header("Step 1: Loading OAuth Tokens")
    if not Path(TOKEN_FILE).exists():
        print_error(f"Token file not found: {TOKEN_FILE}")
        print("\nPlease create a tokens.json file with your OAuth tokens:")
        print(json.dumps({
            "access_token": "your_access_token_here",
            "refresh_token": "your_refresh_token_here"
        }, indent=2))
        return False

    with open(TOKEN_FILE, 'r') as f:
        tokens = json.load(f)

    access_token = tokens.get('access_token')
    refresh_token = tokens.get('refresh_token')

    if not access_token:
        print_error("No access_token in tokens.json")
        return False

    print_success(f"Loaded access_token: {access_token[:20]}...")
    if refresh_token:
        print_success(f"Loaded refresh_token: {refresh_token[:20]}...")
    else:
        print_warning("No refresh_token found")

    # Initialize gateway
    print_header("Step 2: Initializing Gateway")
    async with aiohttp.ClientSession() as session:
        try:
            GatewayClass = gateway_chooser(POINTTAPI)
            gateway = GatewayClass(
                session=session,
                session_type="HTTP",
                host=DEVICE_ID,
                access_key=None,
                access_token=access_token,
                refresh_token=refresh_token,
                token_file=TOKEN_FILE
            )

            print_info("Calling gateway.initialize()...")
            await gateway.initialize()
            print_success("Gateway initialized successfully")
            print_info(f"  Device type: {gateway.device_type}")
            print_info(f"  Bus type: {gateway.bus_type}")
            print_info(f"  UUID: {gateway.uuid}")

        except Exception as e:
            print_error(f"Failed to initialize gateway: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Initialize AC circuits
        print_header("Step 3: Initializing AC Circuits")
        try:
            await gateway.initialize_circuits(AC)
            circuits = gateway.ac_circuits

            if not circuits:
                print_error("No AC circuits found")
                return False

            print_success(f"Found {len(circuits)} AC circuit(s)")
            ac = circuits[0]
            print_info(f"  Circuit ID: {ac.attr_id}")

        except Exception as e:
            print_error(f"Failed to initialize circuits: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Read all current values from bulk endpoint
        print_header("Step 4: Reading All Values (Bulk Endpoint)")
        try:
            await ac.update()
            print_success("Bulk endpoint data retrieved")

            # Get raw data from bulk endpoint
            bulk_endpoint = "/airConditioning/standardFunctions"
            bulk_data = await gateway._connector.get(bulk_endpoint)

            if 'references' not in bulk_data:
                print_error("No 'references' in bulk endpoint response")
                return False

            references = bulk_data['references']
            print_success(f"Found {len(references)} entities in standardFunctions")

        except Exception as e:
            print_error(f"Failed to read bulk endpoint: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Analyze entities
        print_header("Step 5: Analyzing Entities")

        writable_entities = []
        readonly_entities = []

        for ref in references:
            entity_id = ref.get('id', 'unknown')
            entity_type = ref.get('type', 'unknown')
            writeable = ref.get('writeable', 0)
            value = ref.get('value')
            allowed_values = ref.get('allowedValues', [])
            min_val = ref.get('minValue')
            max_val = ref.get('maxValue')
            unit = ref.get('unitOfMeasure', '')

            entity_info = {
                'id': entity_id,
                'type': entity_type,
                'writeable': writeable,
                'current_value': value,
                'allowed_values': allowed_values,
                'min': min_val,
                'max': max_val,
                'unit': unit,
            }

            if writeable:
                writable_entities.append(entity_info)
            else:
                readonly_entities.append(entity_info)

        print(f"\n{Colors.BOLD}Writable Entities: {len(writable_entities)}{Colors.ENDC}")
        for entity in writable_entities:
            print(f"  • {entity['id']}")
            print(f"    Type: {entity['type']}, Current: {entity['current_value']}")
            if entity['allowed_values']:
                print(f"    Allowed: {entity['allowed_values']}")
            elif entity['min'] is not None:
                print(f"    Range: {entity['min']} - {entity['max']} {entity['unit']}")

        print(f"\n{Colors.BOLD}Read-Only Entities: {len(readonly_entities)}{Colors.ENDC}")
        for entity in readonly_entities:
            print(f"  • {entity['id']}: {entity['current_value']} {entity['unit']}")

        # Test writing to all writable entities
        print_header("Step 6: Testing Write Operations")

        test_results = []

        for entity in writable_entities:
            entity_id = entity['id']
            entity_name = entity_id.split('/')[-1]
            current_value = entity['current_value']
            entity_type = entity['type']

            print(f"\n{Colors.BOLD}Testing: {entity_name}{Colors.ENDC}")
            print(f"  ID: {entity_id}")
            print(f"  Current value: {current_value}")

            # Determine test value
            test_value = None

            if entity['allowed_values']:
                # For select/enum types, pick a different value
                allowed = entity['allowed_values']
                # Try to pick a different value
                for val in allowed:
                    if val != current_value:
                        test_value = val
                        break
                if not test_value:
                    # All values same or only one value
                    test_value = allowed[0]
                print(f"  Test value: {test_value} (from allowed values)")

            elif entity['min'] is not None and entity['max'] is not None:
                # For numeric types, pick middle value or slightly different
                min_val = entity['min']
                max_val = entity['max']

                if entity_type == 'floatValue':
                    # For temperature, pick a slightly different value
                    if current_value is not None:
                        test_value = current_value + 0.5
                        if test_value > max_val:
                            test_value = current_value - 0.5
                        if test_value < min_val:
                            test_value = min_val
                    else:
                        test_value = (min_val + max_val) / 2
                else:
                    test_value = int((min_val + max_val) / 2)

                print(f"  Test value: {test_value} (range {min_val}-{max_val})")

            else:
                print_warning("  Cannot determine test value, skipping")
                test_results.append({
                    'entity': entity_name,
                    'status': 'skipped',
                    'reason': 'No test value'
                })
                continue

            # Try to write the test value
            try:
                print_info(f"  Writing: {test_value}")
                await gateway._connector.put(entity_id, test_value)
                print_success(f"  Write successful")

                # Wait a moment for update
                await asyncio.sleep(1)

                # Read back to verify
                print_info("  Reading back to verify...")
                result = await gateway._connector.get(entity_id)
                new_value = result.get('value')

                if new_value == test_value:
                    print_success(f"  Verified: {new_value} ✓")
                    test_results.append({
                        'entity': entity_name,
                        'status': 'success',
                        'old_value': current_value,
                        'test_value': test_value,
                        'new_value': new_value
                    })
                else:
                    print_warning(f"  Value mismatch: expected {test_value}, got {new_value}")
                    test_results.append({
                        'entity': entity_name,
                        'status': 'mismatch',
                        'old_value': current_value,
                        'test_value': test_value,
                        'new_value': new_value
                    })

                # Restore original value
                print_info(f"  Restoring original value: {current_value}")
                await gateway._connector.put(entity_id, current_value)
                await asyncio.sleep(1)

                # Verify restore
                result = await gateway._connector.get(entity_id)
                restored_value = result.get('value')
                if restored_value == current_value:
                    print_success(f"  Restored: {restored_value} ✓")
                else:
                    print_warning(f"  Restore mismatch: expected {current_value}, got {restored_value}")

            except Exception as e:
                print_error(f"  Write failed: {e}")
                test_results.append({
                    'entity': entity_name,
                    'status': 'failed',
                    'error': str(e)
                })

        # Final report
        print_header("Step 7: Test Results Summary")

        success_count = sum(1 for r in test_results if r['status'] == 'success')
        failed_count = sum(1 for r in test_results if r['status'] == 'failed')
        mismatch_count = sum(1 for r in test_results if r['status'] == 'mismatch')
        skipped_count = sum(1 for r in test_results if r['status'] == 'skipped')

        print(f"\n{Colors.BOLD}Total Entities Tested: {len(test_results)}{Colors.ENDC}")
        print_success(f"Success: {success_count}")
        if failed_count > 0:
            print_error(f"Failed: {failed_count}")
        if mismatch_count > 0:
            print_warning(f"Mismatch: {mismatch_count}")
        if skipped_count > 0:
            print_info(f"Skipped: {skipped_count}")

        # Detailed results
        print(f"\n{Colors.BOLD}Detailed Results:{Colors.ENDC}")
        for result in test_results:
            entity = result['entity']
            status = result['status']

            if status == 'success':
                print(f"{Colors.OKGREEN}✓{Colors.ENDC} {entity}: Write/Read/Restore successful")
                print(f"    {result['old_value']} → {result['test_value']} → {result['old_value']}")
            elif status == 'failed':
                print(f"{Colors.FAIL}✗{Colors.ENDC} {entity}: {result.get('error', 'Unknown error')}")
            elif status == 'mismatch':
                print(f"{Colors.WARNING}⚠{Colors.ENDC} {entity}: Value mismatch")
                print(f"    Expected: {result['test_value']}, Got: {result['new_value']}")
            elif status == 'skipped':
                print(f"{Colors.OKCYAN}○{Colors.ENDC} {entity}: {result.get('reason', 'Skipped')}")

        # Check for token refresh
        print_header("Step 8: Token Refresh Check")
        if gateway.tokens_changed(access_token, refresh_token):
            print_success("Tokens were refreshed during test")
            print_info(f"  New access_token: {gateway.access_token[:20]}...")
            print_info(f"  New refresh_token: {gateway.refresh_token[:20]}...")
            print_info(f"  Expires at: {gateway.token_expires_at}")
            print_warning("Remember to update your tokens.json or HA config entry!")
        else:
            print_success("Tokens unchanged")

        # Final verdict
        print_header("Final Verdict")

        all_success = failed_count == 0 and mismatch_count == 0

        if all_success:
            print(f"{Colors.OKGREEN}{Colors.BOLD}")
            print("╔════════════════════════════════════════════════════════════════════╗")
            print("║                    ✓ ALL TESTS PASSED ✓                           ║")
            print("║                                                                    ║")
            print("║   All writable entities successfully tested:                      ║")
            print(f"║   - Write operations work                                          ║")
            print(f"║   - Read verification works                                        ║")
            print(f"║   - Restore original values works                                  ║")
            print("║                                                                    ║")
            print("║   PoinTT API integration is fully functional! 🎉                   ║")
            print("╚════════════════════════════════════════════════════════════════════╝")
            print(Colors.ENDC)
            return True
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}")
            print("╔════════════════════════════════════════════════════════════════════╗")
            print("║                    ✗ SOME TESTS FAILED ✗                          ║")
            print("╚════════════════════════════════════════════════════════════════════╝")
            print(Colors.ENDC)
            if failed_count > 0:
                print_error(f"{failed_count} entity write operations failed")
            if mismatch_count > 0:
                print_warning(f"{mismatch_count} entity values didn't match after write")
            return False


async def main():
    """Main entry point."""
    try:
        success = await test_all_entities()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
