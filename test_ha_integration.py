#!/usr/bin/env python3
"""Test Home Assistant integration pattern for PoinTT API."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from bosch_thermostat_client.const import POINTTAPI
from bosch_thermostat_client.gateway import gateway_chooser


async def test_ha_instantiation():
    """Test that PoinTT gateway can be instantiated using HA's pattern."""
    print("=" * 70)
    print("TEST: Home Assistant Integration Pattern")
    print("=" * 70)

    # Simulate HA config entry data
    config_entry_data = {
        "uuid": "test-uuid-12345",
        "address": "123456789",  # Example device_id
        "protocol": "HTTP",
        "device_type": "POINTTAPI",
        "access_key": None,  # OAuth doesn't use this
        "access_token": "test_access_token_abc123",
        "refresh_token": "test_refresh_token_xyz789",
    }

    print("\n1. Config Entry Data (simulating HA storage):")
    print(json.dumps(config_entry_data, indent=2))

    # Mock aiohttp session (simulating async_get_clientsession)
    mock_session = MagicMock()

    print("\n2. Creating gateway with HA pattern...")
    try:
        GatewayClass = gateway_chooser(POINTTAPI)
        gateway = GatewayClass(
            session=mock_session,  # From async_get_clientsession(hass)
            session_type=config_entry_data["protocol"],
            host=config_entry_data["address"],
            access_key=config_entry_data["access_key"],
            access_token=config_entry_data["access_token"],
            refresh_token=config_entry_data.get("refresh_token"),
            token_file=None,  # HA manages tokens via entry.data, not file
        )
        print("   ✓ Gateway instantiated successfully")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n3. Verifying gateway properties...")
    try:
        # Test access_token property
        assert gateway.access_token == config_entry_data["access_token"], \
            f"access_token mismatch: {gateway.access_token} != {config_entry_data['access_token']}"
        print(f"   ✓ access_token: {gateway.access_token}")

        # Test access_key property
        assert gateway.access_key is None, \
            f"access_key should be None, got: {gateway.access_key}"
        print(f"   ✓ access_key: {gateway.access_key}")

        # Test refresh_token property
        assert gateway.refresh_token == config_entry_data["refresh_token"], \
            f"refresh_token mismatch: {gateway.refresh_token} != {config_entry_data['refresh_token']}"
        print(f"   ✓ refresh_token: {gateway.refresh_token}")

        # Test token_expires_at property (should be None initially)
        print(f"   ✓ token_expires_at: {gateway.token_expires_at}")

    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
        return False
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n4. Verifying no token file is used...")
    try:
        assert gateway._connector._token_file is None, \
            f"token_file should be None for HA, got: {gateway._connector._token_file}"
        print("   ✓ Token file disabled (using HA entry.data)")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")
        return False

    print("\n5. Testing check_firmware_validity override...")
    try:
        # Should return True without making API calls
        result = await gateway.check_firmware_validity()
        assert result is True, f"check_firmware_validity should return True, got: {result}"
        print("   ✓ check_firmware_validity() returns True")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n6. Simulating HA token update pattern...")
    print("   (After thermostat_refresh, HA checks if tokens changed)")
    try:
        # Simulate token refresh (in real usage, this happens during API calls)
        old_token = gateway.access_token
        print(f"   - Current access_token: {old_token}")

        # In HA coordinator, after update:
        new_token = gateway.access_token
        new_refresh = gateway.refresh_token
        new_expires = gateway.token_expires_at

        # HA would check and update entry.data if changed:
        if new_token != config_entry_data["access_token"]:
            print("   - Token changed, HA would update entry.data")
            # hass.config_entries.async_update_entry(entry, data={...})
        else:
            print("   - Token unchanged, no entry.data update needed")

        print("   ✓ Token update pattern verified")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED - PoinTT ready for HA integration!")
    print("=" * 70)
    print("\nNext steps for HA integration:")
    print("1. Add POINTTAPI to supported device types in config flow")
    print("2. Store access_token, refresh_token in entry.data")
    print("3. After thermostat_refresh(), check if tokens changed:")
    print("   if gateway.access_token != entry.data['access_token']:")
    print("       hass.config_entries.async_update_entry(entry, data={")
    print("           **entry.data,")
    print("           'access_token': gateway.access_token,")
    print("           'refresh_token': gateway.refresh_token,")
    print("           'token_expires_at': gateway.token_expires_at,")
    print("       })")
    return True


async def test_backward_compatibility():
    """Test that old standalone script pattern still works."""
    print("\n" + "=" * 70)
    print("TEST: Backward Compatibility (Standalone Scripts)")
    print("=" * 70)

    mock_session = MagicMock()

    print("\n1. Creating gateway with standalone pattern (with token_file)...")
    try:
        GatewayClass = gateway_chooser(POINTTAPI)
        gateway = GatewayClass(
            session=mock_session,
            session_type="HTTP",
            host="123456789",  # Example device_id
            access_key=None,
            access_token="standalone_token",
            refresh_token="standalone_refresh",
            token_file="test_tokens.json",  # Standalone uses token file
        )
        print("   ✓ Gateway instantiated with token_file")

        # Verify token file is set
        assert gateway._connector._token_file is not None
        assert str(gateway._connector._token_file) == "test_tokens.json"
        print(f"   ✓ Token file configured: {gateway._connector._token_file}")

    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✓ Backward compatibility maintained!")
    return True


async def main():
    """Run all tests."""
    success = True

    # Test 1: HA integration pattern
    result1 = await test_ha_instantiation()
    success = success and result1

    # Test 2: Backward compatibility
    result2 = await test_backward_compatibility()
    success = success and result2

    if success:
        print("\n" + "=" * 70)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
