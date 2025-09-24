#!/usr/bin/env python3
"""
Usage Examples for BoschPointtAPI

This file demonstrates how to use the BoschPointtAPI class for various operations.
"""

from bosch_pointt_api import BoschPointtAPI


def example_full_oauth_flow():
    """
    Example: Complete OAuth authentication flow
    """
    print("=== OAuth Authentication Flow ===")

    # Initialize the API client
    api = BoschPointtAPI(token_file="my_tokens.pkl", device_id="101638933")

    # Step 1: Generate OAuth URL
    auth_url = api.build_auth_url()
    print(f"1. Open this URL in your browser: {auth_url}")

    # Step 2: Get the callback URL after user authorization
    callback_url = input("2. Paste the callback URL here: ")

    # Step 3: Extract code and exchange for tokens
    code = api.extract_code_from_url(callback_url)
    if code:
        success = api.exchange_code_for_tokens(code)
        if success:
            print("3. ✓ Authentication successful! Tokens saved.")
        else:
            print("3. ✗ Authentication failed!")
    else:
        print("3. ✗ Could not extract code from URL!")


def example_load_and_refresh_tokens():
    """
    Example: Load existing tokens and refresh if needed
    """
    print("\n=== Token Management ===")

    api = BoschPointtAPI(token_file="my_tokens.pkl", device_id="101638933")

    # Load existing tokens
    if api.load_tokens():
        print("✓ Tokens loaded successfully")

        # Check if token is expired and refresh if needed
        if api.is_token_expired():
            print("Token is expired, refreshing...")
            if api.refresh_access_token():
                print("✓ Token refreshed successfully")
            else:
                print("✗ Token refresh failed")
        else:
            print("✓ Token is still valid")
    else:
        print("✗ Failed to load tokens - need to authenticate first")


def example_api_queries():
    """
    Example: Making various API queries
    """
    print("\n=== API Queries ===")

    api = BoschPointtAPI(token_file="my_tokens.pkl", device_id="101638933")
    api.load_tokens()

    # Get standard functions (most commonly used)
    print("Getting standard functions...")
    result = api.get_standard_functions()
    if result:
        print("✓ Standard functions retrieved")

    # Get current operation mode
    print("\nGetting operation mode...")
    result = api.get_operation_mode()
    if result:
        print("✓ Operation mode retrieved")

    # Get temperature setpoint
    print("\nGetting temperature setpoint...")
    result = api.get_temperature_setpoint()
    if result:
        print("✓ Temperature setpoint retrieved")

    # Get general resource information
    print("\nGetting resource information...")
    result = api.get_resource_info()
    if result:
        print("✓ Resource information retrieved")


def example_set_temperature():
    """
    Example: Setting temperature setpoint
    """
    print("\n=== Setting Temperature ===")

    api = BoschPointtAPI(token_file="my_tokens.pkl", device_id="101638933")
    api.load_tokens()

    # Set temperature to 22.5°C
    target_temp = 22.5
    print(f"Setting temperature to {target_temp}°C...")

    result = api.set_temperature_setpoint(target_temp)
    if result:
        print(f"✓ Temperature setpoint set to {target_temp}°C")
    else:
        print("✗ Failed to set temperature setpoint")


def example_custom_api_request():
    """
    Example: Making custom API requests
    """
    print("\n=== Custom API Request ===")

    api = BoschPointtAPI(token_file="my_tokens.pkl", device_id="101638933")
    api.load_tokens()

    # Make a custom GET request
    print("Making custom API request...")
    result = api.make_api_request("/resource/airConditioning/standardFunctions")
    if result:
        print("✓ Custom request successful")

    # Make a custom PUT request with data
    print("\nMaking custom PUT request...")
    result = api.make_api_request(
        "/resource/airConditioning/temperatureSetpoint",
        method="PUT",
        data={"value": 23.0},
    )
    if result:
        print("✓ Custom PUT request successful")


def example_multiple_devices():
    """
    Example: Working with multiple devices
    """
    print("\n=== Multiple Devices ===")

    # Initialize API without default device
    api = BoschPointtAPI(token_file="my_tokens.pkl")
    api.load_tokens()

    devices = ["101638933", "101638934", "101638935"]  # Example device IDs

    for device_id in devices:
        print(f"\nQuerying device {device_id}...")

        # Query each device explicitly
        result = api.get_standard_functions(device_id=device_id)
        if result:
            print(f"✓ Device {device_id} responded")
        else:
            print(f"✗ Device {device_id} failed to respond")


def example_error_handling():
    """
    Example: Proper error handling
    """
    print("\n=== Error Handling ===")

    api = BoschPointtAPI(token_file="my_tokens.pkl", device_id="101638933")

    try:
        # Try to load tokens
        if not api.load_tokens():
            print("No tokens found - need to authenticate first")
            return

        # Try to make API request
        result = api.get_standard_functions()
        if result is None:
            print("API request failed - check device ID and connectivity")

            # Try to refresh token and retry
            if api.refresh_access_token():
                print("Token refreshed, retrying...")
                result = api.get_standard_functions()
                if result:
                    print("✓ Retry successful after token refresh")
                else:
                    print("✗ Still failing after token refresh")
            else:
                print("✗ Token refresh also failed")
        else:
            print("✓ API request successful")

    except Exception as e:
        print(f"Unexpected error: {e}")


def main():
    """
    Main function to run examples
    """
    print("BoschPointtAPI Usage Examples")
    print("=" * 50)

    # Uncomment the examples you want to run:

    # example_full_oauth_flow()
    # example_load_and_refresh_tokens()
    # example_api_queries()
    # example_set_temperature()
    # example_custom_api_request()
    # example_multiple_devices()
    # example_error_handling()

    print("\nUncomment the examples you want to run in the main() function.")

    # For demonstration, let's run the token management example
    api = BoschPointtAPI()

    # Show OAuth URL generation
    print("\nExample OAuth URL:")
    print(api.build_auth_url())

    print("\nTo use this class:")
    print("1. Run: python bosch_pointt_api.py auth --device YOUR_DEVICE_ID")
    print("2. Complete OAuth flow in browser")
    print("3. Run: python bosch_pointt_api.py query standard --device YOUR_DEVICE_ID")


if __name__ == "__main__":
    main()
