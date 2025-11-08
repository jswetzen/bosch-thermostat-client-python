#!/usr/bin/env python3
"""Interactive test script to verify AC circuit detection and climate capabilities."""

import asyncio
import json
import logging
import sys
from pathlib import Path

import aiohttp

from bosch_thermostat_client.gateway.pointtapi import PoinTTAPIGateway
from bosch_thermostat_client.const import AC

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


def load_config():
    """Load configuration from tokens.json."""
    token_file = Path.home() / ".bosch" / "tokens.json"

    if not token_file.exists():
        print(f"❌ Token file not found: {token_file}")
        print("\nPlease run the OAuth flow first to generate tokens.")
        sys.exit(1)

    try:
        with open(token_file, 'r') as f:
            config = json.load(f)

        required_keys = ['access_token', 'refresh_token', 'device_id']
        missing = [k for k in required_keys if k not in config]

        if missing:
            print(f"❌ Missing required keys in {token_file}: {missing}")
            sys.exit(1)

        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)


async def test_ac_detection():
    """Test AC circuit detection and climate capabilities."""

    print("="*80)
    print("AC CIRCUIT DETECTION TEST")
    print("="*80)
    print()

    # Load config
    config = load_config()
    device_id = config['device_id']
    access_token = config['access_token']
    refresh_token = config['refresh_token']
    token_expires_at = config.get('expires_at')

    print(f"Device ID: {device_id}")
    print(f"Token expires at: {token_expires_at or 'Not set'}")
    print()

    # Create session
    async with aiohttp.ClientSession() as session:
        # Initialize gateway
        print("Initializing gateway...")
        gateway = PoinTTAPIGateway(
            session=session,
            host=device_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
        )

        try:
            # Initialize
            await gateway.initialize()
            print("✓ Gateway initialized successfully\n")

            # Check capabilities
            print("-" * 80)
            print("STEP 1: Testing get_capabilities()")
            print("-" * 80)

            capabilities = await gateway.get_capabilities()

            print(f"Detected capabilities: {capabilities}")
            print()

            if AC in capabilities:
                print(f"✓ SUCCESS: AC ('{AC}') detected in capabilities!")
            else:
                print(f"✗ FAILURE: AC ('{AC}') NOT detected in capabilities")
                print("This means the integration won't create climate entities.")
                return False

            print()

            # Check AC circuits
            print("-" * 80)
            print("STEP 2: Checking AC circuits")
            print("-" * 80)

            ac_circuits = gateway.ac_circuits

            if not ac_circuits:
                print("✗ No AC circuits found!")
                print("This is unexpected since capabilities detected AC.")
                return False

            print(f"✓ Found {len(ac_circuits)} AC circuit(s)")
            print()

            # Examine each AC circuit
            for i, circuit in enumerate(ac_circuits, 1):
                print("-" * 80)
                print(f"STEP 3: AC Circuit #{i} - {circuit.name}")
                print("-" * 80)

                print(f"Circuit ID: {circuit.id}")
                print(f"Circuit Name: {circuit.name}")
                print(f"Circuit Type: {circuit.circuit_type}")
                print(f"State: {circuit.state}")
                print()

                # Check for climate-related sensors
                print("Climate-related sensors:")
                sensors = circuit.sensors if hasattr(circuit, 'sensors') else []

                if sensors:
                    for sensor in sensors:
                        print(f"  - {sensor.name}: {sensor.state} {sensor.units if hasattr(sensor, 'units') else ''}")
                else:
                    print("  (No sensors found)")
                print()

                # Check for climate-related switches
                print("Climate-related switches/controls:")
                switches = circuit.switches if hasattr(circuit, 'switches') else []

                if switches:
                    for switch in switches:
                        print(f"  - {switch.name}: {switch.state}")
                else:
                    print("  (No switches found)")
                print()

                # Check for HA sensors (this is what HA uses)
                print("Home Assistant sensor mapping:")
                ha_sensors = circuit.ha_sensors if hasattr(circuit, 'ha_sensors') else []

                if ha_sensors:
                    for ha_sensor in ha_sensors:
                        print(f"  - {ha_sensor.name}: {ha_sensor.state}")
                else:
                    print("  (No HA sensors found)")
                print()

                # Try to get current temperature
                print("Attempting to read climate data...")

                try:
                    # Try to update data
                    await circuit.update()
                    print("✓ Circuit data updated successfully")

                    # Show all available attributes
                    print("\nAll circuit attributes:")
                    for attr in dir(circuit):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(circuit, attr)
                                if not callable(value):
                                    print(f"  {attr}: {value}")
                            except Exception:
                                pass

                except Exception as e:
                    print(f"✗ Error updating circuit: {e}")

                print()

            # Summary
            print("="*80)
            print("SUMMARY")
            print("="*80)
            print(f"✓ AC detected in capabilities: YES")
            print(f"✓ Number of AC circuits: {len(ac_circuits)}")
            print()
            print("Expected behavior in Home Assistant:")
            print("  1. Integration should see 'ac' in capabilities")
            print("  2. Integration should create climate entities for each AC circuit")
            print("  3. Climate entities should show temperature, mode, fan controls")
            print()

            if len(ac_circuits) > 0:
                print("✓ Test appears successful!")
                print("\nIf HA still doesn't create climate entities, the issue is in the")
                print("Home Assistant integration code, not the library.")
                return True
            else:
                print("✗ Test failed - no AC circuits found")
                return False

        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    result = asyncio.run(test_ac_detection())
    sys.exit(0 if result else 1)
