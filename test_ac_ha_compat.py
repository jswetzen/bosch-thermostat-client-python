#!/usr/bin/env python3
"""Test ACCircuit HA compatibility properties."""

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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


def load_config():
    """Load configuration from tokens.json."""
    token_file = Path(__file__).parent / "tokens.json"

    if not token_file.exists():
        print(f"❌ Token file not found: {token_file}")
        sys.exit(1)

    with open(token_file, 'r') as f:
        return json.load(f)


async def test_ha_compatibility():
    """Test HA compatibility properties on ACCircuit."""

    print("="*80)
    print("AC CIRCUIT - HOME ASSISTANT COMPATIBILITY TEST")
    print("="*80)
    print()

    config = load_config()
    device_id = config['device_id']
    access_token = config['access_token']
    refresh_token = config['refresh_token']
    token_expires_at = config.get('expires_at')

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

        await gateway.initialize()
        print("✓ Gateway initialized\n")

        # Get capabilities
        capabilities = await gateway.get_capabilities()
        print(f"Capabilities: {capabilities}")

        if AC not in capabilities:
            print("❌ AC not in capabilities!")
            return False

        # Get AC circuits
        ac_circuits = gateway.ac_circuits
        if not ac_circuits:
            print("❌ No AC circuits found!")
            return False

        print(f"✓ Found {len(ac_circuits)} AC circuit(s)\n")

        # Test each AC circuit
        for circuit in ac_circuits:
            print("-" * 80)
            print(f"Testing AC Circuit: {circuit.name}")
            print("-" * 80)

            # Update circuit data
            await circuit.update()

            # Check HA compatibility properties
            required_properties = [
                'current_temp',
                'target_temperature',
                'temp_units',
                'min_temp',
                'max_temp',
                'ha_mode',
                'ha_modes',
                'hvac_action',
                'support_presets',
                'state',
            ]

            print("\n✓ Checking required HA properties:")
            all_present = True
            for prop in required_properties:
                if hasattr(circuit, prop):
                    value = getattr(circuit, prop)
                    print(f"  ✓ {prop:25} = {value}")
                else:
                    print(f"  ❌ {prop:25} = MISSING!")
                    all_present = False

            # Check set_ha_mode method
            print("\n✓ Checking HA methods:")
            if hasattr(circuit, 'set_ha_mode'):
                print(f"  ✓ set_ha_mode() exists")
            else:
                print(f"  ❌ set_ha_mode() MISSING!")
                all_present = False

            if not all_present:
                print("\n❌ Some required properties/methods are missing!")
                return False

            # Test mode switching (read-only test)
            print("\n✓ Testing mode properties:")
            print(f"  Current mode: {circuit.ha_mode}")
            print(f"  Available modes: {circuit.ha_modes}")
            print(f"  Current action: {circuit.hvac_action}")

            # Validate mode mapping
            print("\n✓ Validating mode mapping:")
            expected_modes = ["off", "auto", "heat", "cool", "fan_only"]
            if set(circuit.ha_modes) == set(expected_modes):
                print(f"  ✓ All expected HA modes present: {expected_modes}")
            else:
                print(f"  ❌ Mode mismatch!")
                print(f"     Expected: {expected_modes}")
                print(f"     Got:      {circuit.ha_modes}")
                return False

            print("\n" + "="*80)
            print("✓ ALL HA COMPATIBILITY TESTS PASSED!")
            print("="*80)
            print()
            print("ACCircuit is now compatible with Home Assistant's BoschThermostat class!")
            print()
            return True

    return False


if __name__ == "__main__":
    result = asyncio.run(test_ha_compatibility())
    sys.exit(0 if result else 1)
