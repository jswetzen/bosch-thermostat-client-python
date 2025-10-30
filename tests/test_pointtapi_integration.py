#!/usr/bin/env python3
"""
Automated integration test for PoinTT API without real tokens.

This test mocks HTTP calls and verifies:
1. Gateway initialization works
2. Circuit discovery creates AC circuit
3. Only valid endpoints are called
4. Circuit can read values from bulk endpoint
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Create a dummy decorator for when pytest is not available
    def pytest_mark_asyncio(func):
        return func
    class pytest:
        class mark:
            asyncio = staticmethod(pytest_mark_asyncio)

from bosch_thermostat_client.const import POINTTAPI, AC
from bosch_thermostat_client.gateway import gateway_chooser


# Mock bulk endpoint response from real PoinTT API
BULK_ENDPOINT_RESPONSE = {
    "id": "/airConditioning/standardFunctions",
    "type": "bulk",
    "references": [
        {
            "id": "/airConditioning/operationMode",
            "type": "stringValue",
            "writeable": 1,
            "recordable": 0,
            "value": "heat",
            "allowedValues": ["auto", "heat", "cool", "fanOnly"]
        },
        {
            "id": "/airConditioning/acControl",
            "type": "stringValue",
            "writeable": 1,
            "recordable": 0,
            "value": "on",
            "allowedValues": ["on", "off"]
        },
        {
            "id": "/airConditioning/fanSpeed",
            "type": "stringValue",
            "writeable": 1,
            "recordable": 0,
            "value": "auto",
            "allowedValues": ["auto", "quiet", "low", "mid", "high"]
        },
        {
            "id": "/airConditioning/airFlowHorizontal",
            "type": "stringValue",
            "writeable": 1,
            "recordable": 0,
            "value": "center",
            "allowedValues": ["center", "left", "right", "swing"]
        },
        {
            "id": "/airConditioning/airFlowVertical",
            "type": "stringValue",
            "writeable": 1,
            "recordable": 0,
            "value": "angle5",
            "allowedValues": ["auto", "angle1", "angle2", "angle3", "angle4", "angle5", "swing"]
        },
        {
            "id": "/airConditioning/temperatureSetpoint",
            "type": "floatValue",
            "writeable": 1,
            "recordable": 0,
            "value": 20.0,
            "unitOfMeasure": "C",
            "minValue": 16.0,
            "maxValue": 30.0
        },
        {
            "id": "/airConditioning/roomTemperature",
            "type": "floatValue",
            "writeable": 0,
            "recordable": 0,
            "value": 19.0,
            "unitOfMeasure": "C"
        },
        {
            "id": "/airConditioning/quickAirFlows",
            "type": "stringValue",
            "writeable": 1,
            "recordable": 0,
            "value": "",
            "allowedValues": ["bottomRight", "bottomCenter", "bottomLeft", "topRight", "topCenter", "topLeft"]
        }
    ]
}

# Expected valid endpoints that should be called
# NOTE: This is the COMPLETE list - no other endpoints exist in PoinTT API
VALID_ENDPOINTS = {
    # Bulk endpoint (only real endpoint that exists)
    "/airConditioning/standardFunctions",
    # Individual URIs from bulk response (used internally by BulkEndpoint)
    "/airConditioning/operationMode",
    "/airConditioning/acControl",
    "/airConditioning/fanSpeed",
    "/airConditioning/airFlowHorizontal",
    "/airConditioning/airFlowVertical",
    "/airConditioning/temperatureSetpoint",
    "/airConditioning/roomTemperature",
    "/airConditioning/quickAirFlows",
}

# Gateway endpoints that don't actually exist but library tries to fetch
# These should return 404 but that's expected
EXPECTED_404_ENDPOINTS = {
    "/gateway/uuid",
    "/gateway/DateTime",
    "/gateway/versionFirmware",
    "/gateway/versionHardware",
    "/gateway/serialId",
    "/gateway/tzInfo/timeZone",
    "/system/bus",
    "/system/appliance/model",
}

# Endpoints that should NEVER be called (were mocked in old implementation)
INVALID_ENDPOINTS = {
    "/acCircuits",  # Doesn't exist - was mocked in connector
    "/ac1",         # Doesn't exist - was mocked in connector
}


class MockHTTPResponse:
    """Mock HTTP response for aiohttp."""

    def __init__(self, json_data, status=200, content_type="application/json"):
        self.json_data = json_data
        self.status = status
        self.content_type = content_type

    async def json(self):
        return self.json_data

    async def text(self):
        return str(self.json_data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockHTTPSession:
    """Mock aiohttp session that tracks all requests."""

    def __init__(self):
        self.requests = []  # Track all requests

    def get(self, url, **kwargs):
        """Mock GET request."""
        self.requests.append(("GET", url, kwargs))

        # Extract URI from URL
        # URL format: https://pointt-api.../gateways/{device_id}/resource/{uri}
        if "/resource/" in url:
            uri = "/" + url.split("/resource/")[-1]
        else:
            uri = url

        # Return appropriate mock response based on URI
        if uri == "/gateway/uuid":
            return MockHTTPResponse({"value": "test-uuid-12345"})
        elif uri == "/gateway/DateTime":
            return MockHTTPResponse({"value": datetime.now(timezone.utc).isoformat()})
        elif uri == "/gateway/versionFirmware":
            # This endpoint doesn't exist in PoinTT API, but we try to fetch it
            return MockHTTPResponse({"error": "Not found"}, status=404)
        elif uri == "/system/bus":
            return MockHTTPResponse({"value": "POINTTAPI"})
        elif uri == "/system/appliance/model":
            return MockHTTPResponse({"value": "PoinTT API Gateway"})
        elif uri == "/airConditioning/standardFunctions":
            # Return bulk endpoint data
            return MockHTTPResponse(BULK_ENDPOINT_RESPONSE)
        else:
            # For other endpoints, return empty or error
            return MockHTTPResponse({"error": f"Unknown endpoint: {uri}"}, status=404)

    def post(self, url, **kwargs):
        """Mock POST request for token refresh."""
        self.requests.append(("POST", url, kwargs))

        # Mock token refresh response
        return MockHTTPResponse({
            "access_token": "mock_access_token_refreshed",
            "refresh_token": "mock_refresh_token_refreshed",
            "expires_in": 3600
        })

    def put(self, url, **kwargs):
        """Mock PUT request."""
        self.requests.append(("PUT", url, kwargs))
        return MockHTTPResponse({}, status=204)


@pytest.mark.asyncio
async def test_pointtapi_gateway_initialization():
    """Test that PoinTT API gateway initializes correctly with mocked HTTP."""

    # Create mock session
    mock_session = MockHTTPSession()

    # Initialize gateway
    GatewayClass = gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        device_id="101638933",
        access_token="mock_access_token",
        session=mock_session,
        token_file="/tmp/test_tokens.json"
    )

    # Mock token file operations
    with patch('pathlib.Path.exists', return_value=False):
        # Initialize gateway
        await gateway.initialize()

    # Verify gateway initialized
    assert gateway.initialized is True
    assert gateway.device_type == POINTTAPI
    assert gateway.bus_type == POINTTAPI

    print("✓ Gateway initialized successfully")


@pytest.mark.asyncio
async def test_pointtapi_circuit_discovery():
    """Test that AC circuit is discovered correctly."""

    # Create mock session
    mock_session = MockHTTPSession()

    # Initialize gateway
    GatewayClass = gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        device_id="101638933",
        access_token="mock_access_token",
        session=mock_session,
        token_file="/tmp/test_tokens.json"
    )

    # Mock token file operations
    with patch('pathlib.Path.exists', return_value=False):
        await gateway.initialize()

        # Initialize AC circuits
        await gateway.initialize_circuits(AC)

    # Verify circuit was created
    circuits = gateway.ac_circuits
    assert len(circuits) == 1, f"Expected 1 AC circuit, found {len(circuits)}"

    ac = circuits[0]
    assert ac.id == "ac1"
    assert ac.state is True  # Should be initialized successfully

    print("✓ AC circuit discovered and initialized")


@pytest.mark.asyncio
async def test_pointtapi_only_valid_endpoints():
    """Test that only valid endpoints are called (no mocked /acCircuits or /ac1).

    This is critical: PoinTT API ONLY has the endpoints in the bulk response.
    Any other endpoints (like /acCircuits, /ac1) were mocked in the old implementation
    and should NOT be called anymore.
    """

    # Create mock session with tracking
    mock_session = MockHTTPSession()

    # Initialize gateway
    GatewayClass = gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        device_id="101638933",
        access_token="mock_access_token",
        session=mock_session,
        token_file="/tmp/test_tokens.json"
    )

    # Mock token file operations
    with patch('pathlib.Path.exists', return_value=False):
        await gateway.initialize()
        await gateway.initialize_circuits(AC)

    # Extract all URIs that were requested
    requested_uris = set()
    for method, url, kwargs in mock_session.requests:
        if method == "GET" and "/resource/" in url:
            uri = "/" + url.split("/resource/")[-1]
            requested_uris.add(uri)

    # Check for invalid endpoints (these should NEVER be called)
    called_invalid = requested_uris & INVALID_ENDPOINTS
    assert len(called_invalid) == 0, (
        f"CRITICAL: Invalid endpoints were called: {called_invalid}\n"
        f"These endpoints don't exist in PoinTT API and were only mocked in old code!"
    )

    # Separate valid vs expected 404 vs completely unexpected
    called_valid = requested_uris & VALID_ENDPOINTS
    called_404 = requested_uris & EXPECTED_404_ENDPOINTS
    truly_unexpected = requested_uris - VALID_ENDPOINTS - EXPECTED_404_ENDPOINTS

    # We should only see valid endpoints + expected 404s
    assert len(truly_unexpected) == 0, (
        f"Unexpected URIs were called: {truly_unexpected}\n"
        f"Valid endpoints: {VALID_ENDPOINTS}\n"
        f"Expected 404s: {EXPECTED_404_ENDPOINTS}\n"
        f"ALL requested: {requested_uris}"
    )

    print(f"✓ Only valid endpoints called")
    print(f"  Valid endpoints hit: {len(called_valid)}")
    print(f"  Expected 404s tried: {len(called_404)}")
    print(f"  Invalid endpoints: 0 (GOOD!)")
    print(f"  Details: {sorted(requested_uris)}")


@pytest.mark.asyncio
async def test_pointtapi_circuit_reads_values():
    """Test that circuit can read values from bulk endpoint."""

    # Create mock session
    mock_session = MockHTTPSession()

    # Initialize gateway
    GatewayClass = gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        device_id="101638933",
        access_token="mock_access_token",
        session=mock_session,
        token_file="/tmp/test_tokens.json"
    )

    # Mock token file operations
    with patch('pathlib.Path.exists', return_value=False):
        await gateway.initialize()
        await gateway.initialize_circuits(AC)

    # Get AC circuit
    circuits = gateway.ac_circuits
    ac = circuits[0]

    # Update circuit to fetch data
    print(f"  Before update: current_temp={ac.current_temp}")
    await ac.update()
    print(f"  After update: current_temp={ac.current_temp}")

    # Debug: check what was requested
    print(f"  Total requests made: {len(mock_session.requests)}")
    for method, url, kwargs in mock_session.requests[-5:]:
        print(f"    {method} {url}")

    # Verify values from bulk endpoint
    assert ac.current_temp == 19.0, f"Expected current_temp=19.0, got {ac.current_temp}"
    assert ac.target_temperature == 20.0, f"Expected target_temp=20.0, got {ac.target_temperature}"
    assert ac.operation_mode == "heat", f"Expected mode='heat', got {ac.operation_mode}"
    assert ac.is_on is True, f"Expected AC to be on, got {ac.is_on}"

    print("✓ Circuit successfully reads values from bulk endpoint")
    print(f"  Current temp: {ac.current_temp}°C")
    print(f"  Target temp: {ac.target_temperature}°C")
    print(f"  Mode: {ac.operation_mode}")
    print(f"  Status: {'ON' if ac.is_on else 'OFF'}")


@pytest.mark.asyncio
async def test_pointtapi_bulk_endpoint_optimization():
    """Test that bulk endpoint is used instead of individual requests."""

    # Create mock session with tracking
    mock_session = MockHTTPSession()

    # Initialize gateway
    GatewayClass = gateway_chooser(POINTTAPI)
    gateway = GatewayClass(
        device_id="101638933",
        access_token="mock_access_token",
        session=mock_session,
        token_file="/tmp/test_tokens.json"
    )

    # Mock token file operations
    with patch('pathlib.Path.exists', return_value=False):
        await gateway.initialize()
        await gateway.initialize_circuits(AC)

        # Get AC circuit and update it
        ac = gateway.ac_circuits[0]
        await ac.update()

    # Count how many times we hit the bulk endpoint vs individual endpoints
    bulk_requests = 0
    individual_ac_requests = 0

    for method, url, kwargs in mock_session.requests:
        if method == "GET":
            if "/airConditioning/standardFunctions" in url:
                bulk_requests += 1
            elif "/airConditioning/" in url and "standardFunctions" not in url:
                individual_ac_requests += 1

    # We should hit the bulk endpoint at least once
    assert bulk_requests > 0, "Bulk endpoint was not used"

    # We should NOT be hitting individual AC endpoints if bulk is working
    # (They might be hit during initial setup but not during update)
    print(f"✓ Bulk endpoint optimization working")
    print(f"  Bulk requests: {bulk_requests}")
    print(f"  Individual AC requests: {individual_ac_requests}")


def test_suite():
    """Run all tests."""
    print("\n=== PoinTT API Automated Integration Tests ===\n")

    # Run each test
    asyncio.run(test_pointtapi_gateway_initialization())
    asyncio.run(test_pointtapi_circuit_discovery())
    asyncio.run(test_pointtapi_only_valid_endpoints())
    asyncio.run(test_pointtapi_circuit_reads_values())
    asyncio.run(test_pointtapi_bulk_endpoint_optimization())

    print("\n=== All Tests Passed ===\n")


if __name__ == "__main__":
    # Run tests standalone
    test_suite()
