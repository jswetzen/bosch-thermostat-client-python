#!/usr/bin/env python3
"""
Simple integration test script for PoinTT API.

This script demonstrates how to:
1. Initialize the gateway with manual token loading
2. Discover and initialize AC circuits
3. Read current AC state
4. Control the AC unit
"""

import asyncio
import json
import pickle
import aiohttp
import logging
from pathlib import Path

from bosch_thermostat_client.const import POINTTAPI, AC
from bosch_thermostat_client.gateway import gateway_chooser

# Enable debug logging to troubleshoot issues
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')


async def main():
    """Main test function."""

    # Configuration - update these values
    DEVICE_ID = "YOUR_DEVICE_ID"  # Replace with your actual device ID
    TOKEN_FILE = "tokens.json"  # Path to your token file

    print("=== PoinTT API Integration Test ===\n")

    # Load tokens from file
    print(f"1. Loading tokens from {TOKEN_FILE}...")
    try:
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            access_token = tokens.get('access_token')
            print(f"   ✓ Access token loaded")
        else:
            print(f"   ✗ Token file not found: {TOKEN_FILE}")
            print("\n   Please create a tokens.json file with your access_token and refresh_token.")
            print("   Example format:")
            print('   {')
            print('     "access_token": "your_access_token_here",')
            print('     "refresh_token": "your_refresh_token_here"')
            print('   }')
            return
    except Exception as e:
        print(f"   ✗ Error loading tokens: {e}")
        return

    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        # Initialize gateway
        print(f"\n2. Initializing PoinTT API gateway for device {DEVICE_ID}...")
        try:
            GatewayClass = gateway_chooser(POINTTAPI)
            gateway = GatewayClass(
                session=session,
                session_type="HTTP",
                host=DEVICE_ID,
                access_key=None,
                access_token=access_token,
                refresh_token=tokens.get('refresh_token'),
                token_file=TOKEN_FILE
            )
            await gateway.initialize()
            print(f"   ✓ Gateway initialized")
            print(f"   - Device type: {gateway.device_type}")
            print(f"   - Bus type: {gateway.bus_type}")
        except Exception as e:
            print(f"   ✗ Error initializing gateway: {e}")
            import traceback
            traceback.print_exc()
            return

        # Initialize AC circuits
        print(f"\n3. Initializing AC circuits...")
        try:
            await gateway.initialize_circuits(AC)
            circuits = gateway.ac_circuits
            if circuits:
                print(f"   ✓ Found {len(circuits)} AC circuit(s)")
                for circuit in circuits:
                    print(f"   - Circuit ID: {circuit.attr_id}")
            else:
                print(f"   ✗ No AC circuits found")
                # Debug: check gateway state
                if AC in gateway._data and gateway._data[AC]:
                    print(f"   DEBUG: gateway._data[AC] exists")
                    print(f"   DEBUG: gateway._data[AC]._items = {gateway._data[AC]._items}")
                else:
                    print(f"   DEBUG: gateway._data[AC] is None or missing")
                return
        except Exception as e:
            print(f"   ✗ Error initializing circuits: {e}")
            import traceback
            traceback.print_exc()
            return

        # Get first AC circuit
        ac = circuits[0]

        # Read current state
        print(f"\n4. Reading current AC state...")
        try:
            await ac.update()
            print(f"   ✓ Current state:")
            print(f"   - Room temperature: {ac.current_temp}°C")
            print(f"   - Target temperature: {ac.target_temperature}°C")
            print(f"   - Operation mode: {ac.operation_mode}")
            print(f"   - AC control: {'ON' if ac.is_on else 'OFF'}")
            print(f"   - Fan speed: {ac.fan_speed}")
            print(f"   - Horizontal airflow: {ac.air_flow_horizontal}")
            print(f"   - Vertical airflow: {ac.air_flow_vertical}")
        except Exception as e:
            print(f"   ✗ Error reading state: {e}")
            import traceback
            traceback.print_exc()
            return

        # Test control (optional - uncomment to test writing)
        print(f"\n5. Testing AC control (skipped by default)...")
        print(f"   To test control, uncomment the code in the script.")

        # Uncomment below to test writing values:
        # print(f"\n5. Testing AC control...")
        # try:
        #     # Test setting temperature
        #     new_temp = 22.0
        #     print(f"   Setting temperature to {new_temp}°C...")
        #     result = await ac.set_temperature(new_temp)
        #     if result:
        #         print(f"   ✓ Temperature set successfully")
        #     else:
        #         print(f"   ✗ Failed to set temperature")
        #
        #     # Wait a moment and read back
        #     await asyncio.sleep(2)
        #     await ac.update()
        #     print(f"   - New target temperature: {ac.target_temperature}°C")
        # except Exception as e:
        #     print(f"   ✗ Error controlling AC: {e}")
        #     import traceback
        #     traceback.print_exc()

        print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
