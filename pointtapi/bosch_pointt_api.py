#!/usr/bin/env python3
"""
Bosch Pointt API Client

A comprehensive Python client for interacting with the Bosch Pointt API,
including OAuth authentication, token management, and API operations.
"""

import argparse
import base64
import hashlib
import json
import pickle
import sys
import urllib.parse
import webbrowser
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep
from urllib.parse import unquote, urlencode, urlunparse

import requests


class BoschPointtAPI:
    """
    A comprehensive client for the Bosch Pointt API with OAuth authentication.

    This class handles:
    - OAuth 2.0 authentication flow
    - Token storage and refresh
    - API requests to Bosch Pointt endpoints
    """

    # OAuth and API constants
    AUTH_BASE_URL = "https://singlekey-id.com"
    TOKEN_URL = "https://singlekey-id.com/auth/connect/token"
    API_BASE_URL = (
        "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways"
    )

    CLIENT_ID = "762162C0-FA2D-4540-AE66-6489F189FADC"
    REDIRECT_URI = "com.bosch.tt.dashtt.pointt://app/login"
    CODE_VERIFIER = "abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklm"

    SCOPES = [
        "openid",
        "email",
        "profile",
        "offline_access",
        "pointt.gateway.claiming",
        "pointt.gateway.removal",
        "pointt.gateway.list",
        "pointt.gateway.users",
        "pointt.gateway.resource.dashapp",
        "pointt.castt.flow.token-exchange",
        "bacon",
    ]

    def __init__(self, token_file="tokens.pkl", device_id=None):
        """
        Initialize the Bosch Pointt API client.

        Args:
            token_file (str): Path to the file for storing tokens
            device_id (str): Device ID for API requests
        """
        self.token_file = Path(token_file)
        self.device_id = device_id
        self.tokens = {}

    def _generate_code_challenge(self):
        """Generate OAuth2 PKCE code challenge."""
        code_challenge = hashlib.sha256(self.CODE_VERIFIER.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
        return code_challenge.replace("=", "")

    def build_auth_url(self):
        """
        Build the OAuth authorization URL.

        Returns:
            str: The complete OAuth authorization URL
        """
        Components = namedtuple(
            "Components", ["scheme", "netloc", "url", "path", "query", "fragment"]
        )

        code_challenge = self._generate_code_challenge()

        query_params = {
            "redirect_uri": urllib.parse.quote_plus(self.REDIRECT_URI),
            "client_id": self.CLIENT_ID,
            "response_type": "code",
            "prompt": "login",
            "state": "_yUmSV3AjUTXfn6DSZQZ-g",
            "nonce": "5iiIvx5_9goDrYwxxUEorQ",
            "scope": urllib.parse.quote(" ".join(self.SCOPES)),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "style_id": "tt_bsch",
            "suppressed_prompt": "login",
        }

        query_params_encoded = unquote(urlencode(query_params))
        query = urllib.parse.quote(query_params_encoded)

        query_params_new = urllib.parse.quote_plus("/auth/connect/authorize/callback?")
        query_full = "ReturnUrl=" + query_params_new + query + "&f=g4nN"

        return urlunparse(
            Components(
                scheme="https",
                netloc="singlekey-id.com",
                query=query_full,
                path="",
                url="/auth/en-us/login",
                fragment="",
            )
        )

    def exchange_code_for_tokens(self, code):
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code (str): Authorization code from OAuth callback

        Returns:
            bool: True if successful, False otherwise
        """
        data = {
            "grant_type": "authorization_code",
            "scope": " ".join(self.SCOPES),
            "code": code,
            "redirect_uri": self.REDIRECT_URI,
            "client_id": self.CLIENT_ID,
            "code_verifier": self.CODE_VERIFIER,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)

            if response.status_code == 200:
                response_json = response.json()

                if "access_token" in response_json and "refresh_token" in response_json:
                    # Add expiration timestamp
                    expires = datetime.now(timezone.utc) + timedelta(
                        seconds=response_json.get("expires_in", 3600)
                    )
                    response_json["expires"] = expires

                    self.tokens = response_json
                    self.save_tokens()

                    print("✓ Tokens obtained successfully!")
                    print(f"Access token: {response_json['access_token'][:50]}...")
                    print(f"Refresh token: {response_json['refresh_token'][:50]}...")
                    print(f"Expires: {expires}")

                    return True
                else:
                    print("✗ Missing tokens in response")
                    return False
            else:
                print(f"✗ Token exchange failed: {response.status_code}")
                print(response.text)
                return False

        except Exception as e:
            print(f"✗ Error during token exchange: {e}")
            return False

    def extract_code_from_url(self, url):
        """
        Extract authorization code from callback URL.

        Args:
            url (str): The callback URL containing the code

        Returns:
            str: The authorization code, or None if not found
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            return query_params.get("code", [None])[0]
        except Exception as e:
            print(f"✗ Error extracting code from URL: {e}")
            return None

    def save_tokens(self):
        """Save tokens to file."""
        try:
            with open(self.token_file, "wb") as file:
                pickle.dump(self.tokens, file)
            print(f"✓ Tokens saved to {self.token_file}")
        except Exception as e:
            print(f"✗ Error saving tokens: {e}")

    def load_tokens(self):
        """
        Load tokens from file.

        Returns:
            bool: True if tokens loaded successfully, False otherwise
        """
        try:
            if not self.token_file.exists():
                print(f"✗ Token file {self.token_file} not found")
                return False

            with open(self.token_file, "rb") as file:
                self.tokens = pickle.load(file)

            print(f"✓ Tokens loaded from {self.token_file}")
            return True
        except Exception as e:
            print(f"✗ Error loading tokens: {e}")
            return False

    def is_token_expired(self):
        """
        Check if the current access token is expired.

        Returns:
            bool: True if expired or expiration unknown, False if still valid
        """
        if not self.tokens or "expires" not in self.tokens:
            return True

        expires = self.tokens["expires"]
        # Add 5 minute buffer
        return datetime.now(timezone.utc) >= expires - timedelta(minutes=5)

    def refresh_access_token(self):
        """
        Refresh the access token using the refresh token.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.tokens or "refresh_token" not in self.tokens:
            print("✗ No refresh token available")
            return False

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.tokens["refresh_token"],
            "scope": " ".join(self.SCOPES),
            "client_id": self.CLIENT_ID,
            "code_verifier": self.CODE_VERIFIER,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=data)

            if response.status_code == 200:
                response_json = response.json()

                if "access_token" in response_json:
                    # Update tokens
                    expires = datetime.now(timezone.utc) + timedelta(
                        seconds=response_json.get("expires_in", 3600)
                    )
                    response_json["expires"] = expires

                    # Keep the refresh token if not provided in response
                    if "refresh_token" not in response_json:
                        response_json["refresh_token"] = self.tokens["refresh_token"]

                    self.tokens = response_json
                    self.save_tokens()

                    print("✓ Token refreshed successfully!")
                    print(f"New access token: {response_json['access_token'][:50]}...")
                    print(f"Expires: {expires}")

                    return True
                else:
                    print("✗ No access token in refresh response")
                    return False
            else:
                print(f"✗ Token refresh failed: {response.status_code}")
                print(response.text)
                return False

        except Exception as e:
            print(f"✗ Error refreshing token: {e}")
            return False

    def ensure_valid_token(self):
        """
        Ensure we have a valid access token, refreshing if necessary.

        Returns:
            bool: True if we have a valid token, False otherwise
        """
        if not self.tokens:
            print("✗ No tokens available. Please authenticate first.")
            return False

        if self.is_token_expired():
            print("Token is expired, refreshing...")
            return self.refresh_access_token()

        return True

    def make_api_request(self, endpoint, method="GET", data=None, device_id=None):
        """
        Make an API request to the Bosch Pointt API.

        Args:
            endpoint (str): API endpoint (e.g., "/resource/airConditioning/standardFunctions")
            method (str): HTTP method ("GET", "POST", "PUT", etc.)
            data (dict): Request data for POST/PUT requests
            device_id (str): Device ID to use (overrides instance device_id)

        Returns:
            dict: API response data, or None if request failed
        """
        if not self.ensure_valid_token():
            return None

        # Use provided device_id or fall back to instance device_id
        target_device = device_id or self.device_id
        if not target_device:
            print("✗ No device ID specified")
            return None

        url = f"{self.API_BASE_URL}/{target_device}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.tokens['access_token']}",
            "Content-Type": "application/json",
        }

        try:
            print(f"Making {method} request to: {url}")

            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            else:
                print(f"✗ Unsupported HTTP method: {method}")
                return None

            if response.status_code == 200:
                result = response.json()
                print(f"✓ API request successful!")
                print(json.dumps(result, indent=2))
                return result
            else:
                print(f"✗ API request failed: {response.status_code}")
                print(response.text)
                return None

        except Exception as e:
            print(f"✗ Error making API request: {e}")
            return None

    def get_standard_functions(self, device_id=None):
        """Get standard functions for the device."""
        return self.make_api_request(
            "/resource/airConditioning/standardFunctions", device_id=device_id
        )

    def get_operation_mode(self, device_id=None):
        """Get operation mode for the device."""
        return self.make_api_request(
            "/resource/airConditioning/operationMode", device_id=device_id
        )

    def get_temperature_setpoint(self, device_id=None):
        """Get temperature setpoint for the device."""
        return self.make_api_request(
            "/resource/airConditioning/temperatureSetpoint", device_id=device_id
        )

    def set_temperature_setpoint(self, temperature, device_id=None):
        """Set temperature setpoint for the device."""
        return self.make_api_request(
            "/resource/airConditioning/temperatureSetpoint",
            method="PUT",
            data={"value": temperature},
            device_id=device_id,
        )

    def get_resource_info(self, device_id=None):
        """Get general resource information for the device."""
        return self.make_api_request("/resource/", device_id=device_id)


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Bosch Pointt API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s auth                                    # Start OAuth flow
  %(prog)s refresh                                 # Refresh access token
  %(prog)s query standard --device 101638933      # Get standard functions
  %(prog)s query temp --device 101638933          # Get temperature setpoint
  %(prog)s set-temp 22.5 --device 101638933       # Set temperature to 22.5°C
        """,
    )

    parser.add_argument(
        "--token-file",
        default="tokens.pkl",
        help="Path to token storage file (default: tokens.pkl)",
    )

    parser.add_argument("--device", help="Device ID for API requests")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Auth command
    auth_parser = subparsers.add_parser("auth", help="Start OAuth authentication flow")
    auth_parser.add_argument(
        "--no-browser", action="store_true", help="Don't automatically open browser"
    )

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh access token")

    # Query command
    query_parser = subparsers.add_parser("query", help="Make API queries")
    query_subparsers = query_parser.add_subparsers(
        dest="query_type", help="Query types"
    )

    query_subparsers.add_parser("standard", help="Get standard functions")
    query_subparsers.add_parser("mode", help="Get operation mode")
    query_subparsers.add_parser("temp", help="Get temperature setpoint")
    query_subparsers.add_parser("resource", help="Get resource information")

    # Set temperature command
    set_temp_parser = subparsers.add_parser("set-temp", help="Set temperature setpoint")
    set_temp_parser.add_argument("temperature", type=float, help="Target temperature")

    # Custom query command
    custom_parser = subparsers.add_parser("custom", help="Make custom API request")
    custom_parser.add_argument(
        "endpoint",
        help="API endpoint (e.g., /resource/airConditioning/standardFunctions)",
    )
    custom_parser.add_argument(
        "--method", default="GET", help="HTTP method (default: GET)"
    )
    custom_parser.add_argument("--data", help="JSON data for POST/PUT requests")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize API client
    api = BoschPointtAPI(token_file=args.token_file, device_id=args.device)

    if args.command == "auth":
        print("Starting OAuth authentication flow...")

        # Generate and display auth URL
        auth_url = api.build_auth_url()
        print(f"\nAuth URL: {auth_url}")

        # Open browser unless disabled
        if not args.no_browser:
            print("\nOpening browser...")
            webbrowser.open(auth_url, new=2)
            sleep(2)

        # Get callback URL from user
        callback_url = input("\nPlease enter the callback URL after authorization: ")

        # Extract code and exchange for tokens
        code = api.extract_code_from_url(callback_url)
        if code:
            if api.exchange_code_for_tokens(code):
                print("\n✓ Authentication successful!")
            else:
                print("\n✗ Authentication failed!")
                sys.exit(1)
        else:
            print("\n✗ Could not extract code from URL!")
            sys.exit(1)

    elif args.command == "refresh":
        print("Refreshing access token...")
        api.load_tokens()
        if api.refresh_access_token():
            print("✓ Token refresh successful!")
        else:
            print("✗ Token refresh failed!")
            sys.exit(1)

    elif args.command == "query":
        if not args.device:
            print("✗ Device ID is required for queries. Use --device option.")
            sys.exit(1)

        api.load_tokens()

        if args.query_type == "standard":
            api.get_standard_functions()
        elif args.query_type == "mode":
            api.get_operation_mode()
        elif args.query_type == "temp":
            api.get_temperature_setpoint()
        elif args.query_type == "resource":
            api.get_resource_info()
        else:
            print("✗ Unknown query type. Use: standard, mode, temp, or resource")
            sys.exit(1)

    elif args.command == "set-temp":
        if not args.device:
            print(
                "✗ Device ID is required for setting temperature. Use --device option."
            )
            sys.exit(1)

        api.load_tokens()
        result = api.set_temperature_setpoint(args.temperature)
        if result:
            print(f"✓ Temperature setpoint set to {args.temperature}°C")
        else:
            print("✗ Failed to set temperature setpoint")
            sys.exit(1)

    elif args.command == "custom":
        if not args.device:
            print("✗ Device ID is required for API requests. Use --device option.")
            sys.exit(1)

        api.load_tokens()

        data = None
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON data: {e}")
                sys.exit(1)

        api.make_api_request(args.endpoint, method=args.method, data=data)


if __name__ == "__main__":
    main()
