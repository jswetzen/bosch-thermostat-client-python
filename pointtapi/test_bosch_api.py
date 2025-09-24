#!/usr/bin/env python3
"""
Test script for BoschPointtAPI class functionality.
"""

import sys
import json
from pathlib import Path

# Add the current directory to the path so we can import our module
sys.path.insert(0, str(Path(__file__).parent))

from bosch_pointt_api import BoschPointtAPI


def test_url_generation():
    """Test OAuth URL generation."""
    print("=== Testing OAuth URL Generation ===")

    api = BoschPointtAPI()
    url = api.build_auth_url()

    print(f"Generated OAuth URL: {url}")

    # Basic checks
    assert "singlekey-id.com" in url
    assert "client_id=762162C0-FA2D-4540-AE66-6489F189FADC" in url
    assert "response_type=code" in url

    print("✓ OAuth URL generation test passed!")
    return True


def test_code_extraction():
    """Test code extraction from callback URL."""
    print("\n=== Testing Code Extraction ===")

    api = BoschPointtAPI()

    # Test with valid callback URL
    test_url = "com.bosch.tt.dashtt.pointt://app/login?code=test123&state=somestate"
    code = api.extract_code_from_url(test_url)

    print(f"Extracted code: {code}")
    assert code == "test123"

    # Test with invalid URL
    invalid_url = "com.bosch.tt.dashtt.pointt://app/login?error=access_denied"
    code = api.extract_code_from_url(invalid_url)

    print(f"Code from invalid URL: {code}")
    assert code is None

    print("✓ Code extraction test passed!")
    return True


def test_token_management():
    """Test token save/load functionality."""
    print("\n=== Testing Token Management ===")

    test_file = Path("test_tokens.pkl")
    api = BoschPointtAPI(token_file=test_file)

    # Test tokens
    test_tokens = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    # Set and save tokens
    api.tokens = test_tokens
    api.save_tokens()

    # Clear tokens and reload
    api.tokens = {}
    success = api.load_tokens()

    print(f"Token load success: {success}")
    print(f"Loaded tokens: {api.tokens}")

    assert success
    assert api.tokens["access_token"] == "test_access_token"
    assert api.tokens["refresh_token"] == "test_refresh_token"

    # Clean up
    if test_file.exists():
        test_file.unlink()

    print("✓ Token management test passed!")
    return True


def test_token_expiration():
    """Test token expiration checking."""
    print("\n=== Testing Token Expiration ===")

    from datetime import datetime, timezone, timedelta

    api = BoschPointtAPI()

    # Test with no tokens
    assert api.is_token_expired() == True
    print("✓ No tokens correctly identified as expired")

    # Test with expired token
    api.tokens = {"expires": datetime.now(timezone.utc) - timedelta(hours=1)}
    assert api.is_token_expired() == True
    print("✓ Expired token correctly identified")

    # Test with valid token
    api.tokens = {"expires": datetime.now(timezone.utc) + timedelta(hours=1)}
    assert api.is_token_expired() == False
    print("✓ Valid token correctly identified")

    print("✓ Token expiration test passed!")
    return True


def test_api_methods():
    """Test API method definitions."""
    print("\n=== Testing API Methods ===")

    api = BoschPointtAPI(device_id="test_device")

    # Test that methods exist and can be called (they'll fail due to no auth, but that's expected)
    methods_to_test = [
        "get_standard_functions",
        "get_operation_mode",
        "get_temperature_setpoint",
        "get_resource_info",
    ]

    for method_name in methods_to_test:
        method = getattr(api, method_name)
        assert callable(method)
        print(f"✓ Method {method_name} exists and is callable")

    # Test set_temperature_setpoint with parameter
    method = getattr(api, "set_temperature_setpoint")
    assert callable(method)
    print("✓ Method set_temperature_setpoint exists and is callable")

    print("✓ API methods test passed!")
    return True


def test_device_id_handling():
    """Test device ID parameter handling."""
    print("\n=== Testing Device ID Handling ===")

    # Test with instance device ID
    api = BoschPointtAPI(device_id="instance_device")
    assert api.device_id == "instance_device"
    print("✓ Instance device ID set correctly")

    # Test without device ID
    api = BoschPointtAPI()
    assert api.device_id is None
    print("✓ No device ID handled correctly")

    print("✓ Device ID handling test passed!")
    return True


def main():
    """Run all tests."""
    print("Starting BoschPointtAPI tests...\n")

    tests = [
        test_url_generation,
        test_code_extraction,
        test_token_management,
        test_token_expiration,
        test_api_methods,
        test_device_id_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"✗ Test {test.__name__} failed!")
        except Exception as e:
            failed += 1
            print(f"✗ Test {test.__name__} failed with exception: {e}")

    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
