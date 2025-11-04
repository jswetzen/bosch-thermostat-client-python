#!/usr/bin/env python3
"""Test PoinTT API token refresh and HA integration pattern."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from bosch_thermostat_client.const import POINTTAPI
import bosch_thermostat_client as bosch


async def test_token_refresh_updates_properties():
    """Test that token refresh updates gateway properties."""
    print("=" * 70)
    print("TEST: Token Refresh Updates Gateway Properties")
    print("=" * 70)

    device_id = "123456789"
    initial_access_token = "initial_access_token_abc123"
    initial_refresh_token = "initial_refresh_token_xyz789"

    # Create mock session
    session = MagicMock()
    session.get = MagicMock()
    session.get.__name__ = "get"

    # Mock token refresh response
    refreshed_access_token = "refreshed_access_token_NEW123"
    refreshed_refresh_token = "refreshed_refresh_token_NEW789"

    mock_token_response = MagicMock()
    mock_token_response.status = 200
    mock_token_response.json = AsyncMock(return_value={
        'access_token': refreshed_access_token,
        'refresh_token': refreshed_refresh_token,
        'expires_in': 3600,
        'token_type': 'Bearer'
    })

    session.post = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_token_response)))

    print("\n1. Creating gateway with initial tokens...")
    GatewayClass = bosch.gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        session=session,
        session_type="HTTP",
        host=device_id,
        access_key=None,
        access_token=initial_access_token,
        refresh_token=initial_refresh_token,
        token_file=None,  # HA mode - no file
    )

    print(f"   Initial access_token: {gateway.access_token[:20]}...")
    print(f"   Initial refresh_token: {gateway.refresh_token[:20]}...")

    assert gateway.access_token == initial_access_token
    assert gateway.refresh_token == initial_refresh_token

    print("\n2. Simulating token expiration...")
    # Force token to be expired
    gateway._connector._token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    print(f"   Token expired: {gateway._connector._is_token_expired()}")
    assert gateway._connector._is_token_expired() == True

    print("\n3. Triggering token refresh via _ensure_valid_token()...")
    try:
        await gateway._connector._ensure_valid_token()
        print("   ✓ Token refresh completed")
    except Exception as e:
        print(f"   ✗ Token refresh failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n4. Verifying gateway properties show NEW tokens...")
    print(f"   Current access_token: {gateway.access_token[:20]}...")
    print(f"   Current refresh_token: {gateway.refresh_token[:20]}...")

    # THE CRITICAL TEST: Did the properties update?
    if gateway.access_token != refreshed_access_token:
        print(f"   ✗ FAILED: access_token not updated!")
        print(f"      Expected: {refreshed_access_token[:20]}...")
        print(f"      Got: {gateway.access_token[:20]}...")
        return False

    if gateway.refresh_token != refreshed_refresh_token:
        print(f"   ✗ FAILED: refresh_token not updated!")
        print(f"      Expected: {refreshed_refresh_token[:20]}...")
        print(f"      Got: {gateway.refresh_token[:20]}...")
        return False

    print("   ✓ access_token property returns NEW token")
    print("   ✓ refresh_token property returns NEW token")

    print("\n5. Checking token_expires_at property...")
    expires_at = gateway.token_expires_at
    print(f"   Token expires at: {expires_at}")
    assert expires_at is not None
    print("   ✓ token_expires_at is set")

    print("\n" + "=" * 70)
    print("✓ Token Refresh Properties Test PASSED")
    print("=" * 70)
    return True


async def test_ha_restart_scenario():
    """Test HA restart scenario with stored tokens."""
    print("\n" + "=" * 70)
    print("TEST: HA Restart Scenario")
    print("=" * 70)

    device_id = "123456789"

    # Simulate what HA has stored in config entry
    stored_access_token = "stored_access_token_abc123"
    stored_refresh_token = "stored_refresh_token_xyz789"

    print("\n1. Simulating HA restart - loading tokens from config entry...")
    print(f"   Loaded access_token: {stored_access_token[:20]}...")
    print(f"   Loaded refresh_token: {stored_refresh_token[:20]}...")

    # Create mock session
    session = MagicMock()
    session.get = MagicMock()
    session.get.__name__ = "get"

    # Mock token refresh (token is expired, needs refresh)
    new_access_token = "new_access_token_FRESH123"
    new_refresh_token = "new_refresh_token_FRESH789"

    mock_token_response = MagicMock()
    mock_token_response.status = 200
    mock_token_response.json = AsyncMock(return_value={
        'access_token': new_access_token,
        'refresh_token': new_refresh_token,
        'expires_in': 3600,
        'token_type': 'Bearer'
    })

    session.post = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_token_response)))

    print("\n2. Creating gateway with stored tokens (HA restart)...")
    GatewayClass = bosch.gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        session=session,
        session_type="HTTP",
        host=device_id,
        access_key=None,
        access_token=stored_access_token,  # From entry.data
        refresh_token=stored_refresh_token,  # From entry.data
        token_file=None,  # HA doesn't use token file
    )
    print("   ✓ Gateway created with stored credentials")

    print("\n3. Force token expiration (simulating expired stored token)...")
    gateway._connector._token_expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    print(f"   Token expired: {gateway._connector._is_token_expired()}")

    print("\n4. Calling check_connection() (HA does this on restart)...")
    try:
        # This will trigger token refresh if needed
        await gateway.check_connection()
        print("   ✓ check_connection() succeeded")
    except Exception as e:
        print(f"   ✗ check_connection() failed: {e}")
        return False

    print("\n5. Reading tokens from gateway properties (HA should do this)...")
    current_access_token = gateway.access_token
    current_refresh_token = gateway.refresh_token
    current_expires_at = gateway.token_expires_at

    print(f"   Current access_token: {current_access_token[:20]}...")
    print(f"   Current refresh_token: {current_refresh_token[:20]}...")
    print(f"   Expires at: {current_expires_at}")

    print("\n6. Checking if tokens changed (HA should update entry.data)...")
    if current_access_token != stored_access_token:
        print(f"   ✓ Token CHANGED - HA should update entry.data")
        print(f"      Old: {stored_access_token[:20]}...")
        print(f"      New: {current_access_token[:20]}...")

        # Simulate HA updating config entry
        print("\n   Simulating HA update:")
        print("   hass.config_entries.async_update_entry(entry, data={")
        print("       **entry.data,")
        print(f"       'access_token': '{current_access_token[:20]}...',")
        print(f"       'refresh_token': '{current_refresh_token[:20]}...',")
        print(f"       'token_expires_at': '{current_expires_at}',")
        print("   })")
    else:
        print(f"   ✓ Token unchanged - no update needed")

    print("\n" + "=" * 70)
    print("✓ HA Restart Scenario Test PASSED")
    print("=" * 70)
    return True


async def test_token_change_detection():
    """Test helper method to detect token changes for HA."""
    print("\n" + "=" * 70)
    print("TEST: Token Change Detection Helper")
    print("=" * 70)

    device_id = "123456789"
    initial_token = "initial_token_abc123"

    # Create mock session
    session = MagicMock()
    session.get = MagicMock()
    session.get.__name__ = "get"

    print("\n1. Creating gateway...")
    GatewayClass = bosch.gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        session=session,
        session_type="HTTP",
        host=device_id,
        access_key=None,
        access_token=initial_token,
        refresh_token="refresh_token",
        token_file=None,
    )

    print("\n2. Simulating HA storing initial token...")
    stored_token = gateway.access_token
    print(f"   Stored in entry.data: {stored_token[:20]}...")

    print("\n3. Simulating token refresh...")
    # Manually update connector token (simulating refresh)
    new_token = "new_token_xyz789"
    gateway._connector._access_token = new_token
    print(f"   Token refreshed to: {new_token[:20]}...")

    print("\n4. HA checks for token change (e.g., in thermostat_refresh)...")
    current_token = gateway.access_token

    if current_token != stored_token:
        print(f"   ✓ TOKEN CHANGED detected!")
        print(f"      Stored:  {stored_token[:20]}...")
        print(f"      Current: {current_token[:20]}...")
        print("\n   HA should update entry.data now")

        # This is what HA should do:
        # hass.config_entries.async_update_entry(entry, data={
        #     **entry.data,
        #     'access_token': gateway.access_token,
        #     'refresh_token': gateway.refresh_token,
        #     'token_expires_at': gateway.token_expires_at,
        # })
    else:
        print(f"   Token unchanged")

    assert current_token == new_token, "Property should return updated token"
    print("   ✓ gateway.access_token returns live value")

    print("\n" + "=" * 70)
    print("✓ Token Change Detection Test PASSED")
    print("=" * 70)
    return True


async def main():
    """Run all token refresh tests."""
    print("\n" + "=" * 70)
    print("TESTING: Token Refresh and HA Integration")
    print("=" * 70)

    tests = [
        ("Token Refresh Updates Properties", test_token_refresh_updates_properties),
        ("HA Restart Scenario", test_ha_restart_scenario),
        ("Token Change Detection", test_token_change_detection),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n" + "=" * 70)
        print("✓✓✓ ALL TOKEN REFRESH TESTS PASSED ✓✓✓")
        print("=" * 70)
        print("\nToken refresh mechanism works correctly!")
        print("Tokens ARE available via gateway properties.")
        print("\nHA Integration Pattern:")
        print("1. After any gateway operation, check:")
        print("   if gateway.access_token != entry.data['access_token']:")
        print("       # Update config entry with new tokens")
        print("2. Properties return LIVE values from connector")
        print("3. Token refresh happens automatically via _ensure_valid_token()")
        return 0
    else:
        print("\n" + "=" * 70)
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
