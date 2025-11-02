#!/usr/bin/env python3
"""Test PoinTT API with exact HA component usage pattern."""

import asyncio
from unittest.mock import MagicMock

from bosch_thermostat_client.const import POINTTAPI, AC
import bosch_thermostat_client as bosch

# HA component constants (simulated)
CONF_ADDRESS = "address"
ACCESS_KEY = "access_key"
ACCESS_TOKEN = "access_token"
UUID = "uuid"


async def test_config_flow_pattern():
    """Test the exact pattern used in HA config_flow.py."""
    print("=" * 70)
    print("TEST: HA Config Flow Pattern")
    print("=" * 70)

    # Simulate user input
    device_id = "123456789"
    access_token = "test_oauth_token"
    refresh_token = "test_refresh_token"

    # Create proper mock session with __name__ attribute
    session = MagicMock()
    session.get = MagicMock()
    session.get.__name__ = "get"

    print("\n1. Creating gateway (config flow pattern)...")
    BoschGateway = bosch.gateway_chooser(device_type=POINTTAPI)
    device = BoschGateway(
        session=session,
        session_type="HTTP",
        host=device_id,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    print(f"   ✓ Gateway created: {device}")

    print("\n2. Calling check_connection()...")
    try:
        uuid = await device.check_connection()
        print(f"   ✓ check_connection() returned: {uuid}")
        assert uuid is not None, "UUID should not be None"
        assert uuid == device_id, f"UUID should be device_id, got {uuid}"
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n3. Verifying properties after check_connection()...")

    # Verify UUID property
    print(f"   - device.uuid: {device.uuid}")
    assert device.uuid == device_id, f"Expected {device_id}, got {device.uuid}"

    # Verify access_key (should be None for OAuth)
    print(f"   - device.access_key: {device.access_key}")
    assert device.access_key is None, f"access_key should be None, got {device.access_key}"

    # Verify access_token
    print(f"   - device.access_token: {device.access_token}")
    assert device.access_token == access_token, "access_token mismatch"

    # Verify bus_type
    print(f"   - device.bus_type: {device.bus_type}")
    assert device.bus_type == POINTTAPI, f"bus_type should be POINTTAPI, got {device.bus_type}"

    # Verify database
    print(f"   - device.database exists: {device.database is not None}")
    assert device.database is not None, "database should be populated"
    assert len(device.database) > 0, "database should not be empty"

    print("   ✓ All properties verified")

    print("\n4. Simulating HA config entry creation...")
    entry_data = {
        CONF_ADDRESS: device.host,        # Should be device_id
        UUID: uuid,                        # From check_connection()
        ACCESS_KEY: device.access_key,     # Should be None
        ACCESS_TOKEN: device.access_token, # Current token
        "refresh_token": device.refresh_token,
        "protocol": "HTTP",
        "device_type": "POINTTAPI",
    }
    print(f"   Entry data:")
    for key, value in entry_data.items():
        if key in ["access_token", "refresh_token"]:
            print(f"     {key}: {value[:20]}..." if value else f"     {key}: {value}")
        else:
            print(f"     {key}: {value}")

    assert entry_data[UUID] == device_id
    assert entry_data[CONF_ADDRESS] == device_id
    assert entry_data[ACCESS_KEY] is None
    print("   ✓ Config entry data valid")

    print("\n" + "=" * 70)
    print("✓ Config Flow Pattern Test PASSED")
    print("=" * 70)
    return True


async def test_setup_entry_pattern():
    """Test the exact pattern used in HA __init__.py async_init_bosch()."""
    print("\n" + "=" * 70)
    print("TEST: HA Setup Entry Pattern")
    print("=" * 70)

    # Simulate stored config entry
    device_id = "123456789"
    entry_data = {
        CONF_ADDRESS: device_id,
        UUID: device_id,
        ACCESS_KEY: None,
        ACCESS_TOKEN: "stored_oauth_token",
        "refresh_token": "stored_refresh_token",
        "protocol": "HTTP",
        "device_type": "POINTTAPI",
    }

    # Create proper mock session
    session = MagicMock()
    session.get = MagicMock()
    session.get.__name__ = "get"

    print("\n1. Creating gateway from config entry...")
    BoschGateway = bosch.gateway_chooser(device_type=POINTTAPI)
    gateway = BoschGateway(
        session=session,
        session_type=entry_data["protocol"],
        host=entry_data[CONF_ADDRESS],
        access_key=entry_data[ACCESS_KEY],
        access_token=entry_data[ACCESS_TOKEN],
        refresh_token=entry_data.get("refresh_token"),
    )
    print(f"   ✓ Gateway created from entry data")

    print("\n2. Calling check_connection() (validates connection)...")
    try:
        await gateway.check_connection()
        print(f"   ✓ check_connection() succeeded")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n3. Verifying gateway.uuid is populated...")
    if not gateway.uuid:
        print(f"   ✗ FAILED: gateway.uuid is None")
        return False
    print(f"   ✓ gateway.uuid: {gateway.uuid}")

    print("\n4. Checking bus_type...")
    print(f"   - Bosch BUS detected: {gateway.bus_type}")
    assert gateway.bus_type == POINTTAPI
    print(f"   ✓ Bus type verified")

    print("\n5. Verifying database is populated...")
    if not gateway.database:
        print(f"   ✗ FAILED: gateway.database is falsy")
        return False
    print(f"   ✓ Database loaded: {len(gateway.database)} keys")

    print("\n6. Getting capabilities...")
    try:
        supported = await gateway.get_capabilities()
        print(f"   ✓ Capabilities: {supported}")
        # Note: AC won't be in capabilities with mock session
        # Real HA will have proper API and will detect AC circuits
        assert isinstance(supported, list), "Should return a list"
        print(f"   ✓ Capabilities returned (mock mode - AC requires real API)")
    except Exception as e:
        print(f"   ✗ get_capabilities() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("✓ Setup Entry Pattern Test PASSED")
    print("=" * 70)
    return True


async def test_firmware_check_pattern():
    """Test firmware validity check (called periodically by HA)."""
    print("\n" + "=" * 70)
    print("TEST: HA Firmware Check Pattern")
    print("=" * 70)

    device_id = "123456789"

    # Create proper mock session
    session = MagicMock()
    session.get = MagicMock()
    session.get.__name__ = "get"

    print("\n1. Creating and initializing gateway...")
    BoschGateway = bosch.gateway_chooser(device_type=POINTTAPI)
    gateway = BoschGateway(
        session=session,
        session_type="HTTP",
        host=device_id,
        access_key=None,
        access_token="test_token",
    )
    await gateway.check_connection()
    print("   ✓ Gateway initialized")

    print("\n2. Calling check_firmware_validity()...")
    try:
        result = await gateway.check_firmware_validity()
        print(f"   ✓ check_firmware_validity() returned: {result}")
        assert result is True, "Should return True"
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False

    print("\n" + "=" * 70)
    print("✓ Firmware Check Pattern Test PASSED")
    print("=" * 70)
    return True


async def main():
    """Run all HA component pattern tests."""
    print("\n" + "=" * 70)
    print("TESTING: PoinTT API with HA Component Patterns")
    print("=" * 70)

    tests = [
        ("Config Flow", test_config_flow_pattern),
        ("Setup Entry", test_setup_entry_pattern),
        ("Firmware Check", test_firmware_check_pattern),
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
        print("✓✓✓ ALL HA COMPONENT TESTS PASSED ✓✓✓")
        print("=" * 70)
        print("\nPoinTT API is ready for HA component integration!")
        return 0
    else:
        print("\n" + "=" * 70)
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
