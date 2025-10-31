#!/usr/bin/env python3
"""Debug script to trace token refresh behavior."""

import asyncio
import json
import aiohttp
import logging
from pathlib import Path

from bosch_thermostat_client.const import POINTTAPI, AC
from bosch_thermostat_client.gateway import gateway_chooser

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

async def main():
    DEVICE_ID = "YOUR_DEVICE_ID"  # Replace with your actual device ID
    TOKEN_FILE = "tokens.json"

    print("=" * 70)
    print("DEBUG: Token Refresh Trace")
    print("=" * 70)

    # Show current tokens
    print("\n1. Current tokens.json:")
    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
        print(f"   - access_token: {tokens.get('access_token', 'MISSING')[:20]}...")
        print(f"   - refresh_token: {tokens.get('refresh_token', 'MISSING')[:20] if tokens.get('refresh_token') else 'MISSING'}")
        print(f"   - expires_at: {tokens.get('expires_at', 'MISSING')}")
    else:
        print(f"   ERROR: {TOKEN_FILE} not found!")
        return

    async with aiohttp.ClientSession() as session:
        print("\n2. Creating gateway...")
        GatewayClass = gateway_chooser(POINTTAPI)
        gateway = GatewayClass(
            session=session,
            session_type="HTTP",
            host=DEVICE_ID,
            access_key=None,
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            token_file=TOKEN_FILE
        )

        # Check connector state before initialization
        print("\n3. Connector state BEFORE initialize():")
        print(f"   - _access_token: {gateway._connector._access_token[:20]}...")
        print(f"   - _refresh_token: {gateway._connector._refresh_token[:20] if gateway._connector._refresh_token else 'None'}")
        print(f"   - _token_expires_at: {gateway._connector._token_expires_at}")
        print(f"   - _is_token_expired(): {gateway._connector._is_token_expired()}")

        print("\n4. Calling gateway.initialize()...")
        try:
            await gateway.initialize()
            print("   SUCCESS!")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return

        # Check connector state after initialization
        print("\n5. Connector state AFTER initialize():")
        print(f"   - _access_token: {gateway._connector._access_token[:20]}...")
        print(f"   - _refresh_token: {gateway._connector._refresh_token[:20] if gateway._connector._refresh_token else 'None'}")
        print(f"   - _token_expires_at: {gateway._connector._token_expires_at}")

        # Check tokens.json
        print("\n6. tokens.json AFTER initialize():")
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            print(f"   - access_token: {tokens.get('access_token', 'MISSING')[:20]}...")
            print(f"   - refresh_token: {tokens.get('refresh_token', 'MISSING')[:20] if tokens.get('refresh_token') else 'MISSING'}")
            print(f"   - expires_at: {tokens.get('expires_at', 'MISSING')}")

        print("\n7. Attempting to initialize circuits...")
        try:
            await gateway.initialize_circuits(AC)
            circuits = gateway.ac_circuits  # Access via property, not return value
            print(f"   Found {len(circuits)} circuits")

            # Debug: Check if circuit was created but filtered out
            if len(circuits) == 0:
                print("\n   DEBUG: No circuits found - checking gateway._data...")
                if AC in gateway._data and gateway._data[AC]:
                    print(f"   - gateway._data[AC] exists: {gateway._data[AC]}")
                    print(f"   - gateway._data[AC]._items: {gateway._data[AC]._items}")
                else:
                    print(f"   - gateway._data[AC] is None or missing")

        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return

        # Check tokens.json after circuit initialization
        print("\n8. tokens.json AFTER circuit init:")
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            print(f"   - access_token: {tokens.get('access_token', 'MISSING')[:20]}...")
            print(f"   - refresh_token: {tokens.get('refresh_token', 'MISSING')[:20] if tokens.get('refresh_token') else 'MISSING'}")
            print(f"   - expires_at: {tokens.get('expires_at', 'MISSING')}")

        if circuits:
            ac = circuits[0]
            print("\n9. Attempting to read AC state...")
            try:
                await ac.update()
                print(f"   Room temp: {ac.current_temp}°C")
                print(f"   Target temp: {ac.target_temperature}°C")
            except Exception as e:
                print(f"   ERROR: {e}")
                import traceback
                traceback.print_exc()

        # Final check
        print("\n10. FINAL tokens.json:")
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            print(json.dumps(tokens, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
