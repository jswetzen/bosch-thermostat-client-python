"""Comprehensive test suite for PoinTT API connector and functionality."""

import unittest
import json
import tempfile
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from bosch_thermostat_client.connectors.pointtapi import PoinTTAPIConnector
from bosch_thermostat_client.gateway.pointtapi import PoinTTAPIGateway
from bosch_thermostat_client.const import POINTTAPI
from bosch_thermostat_client.exceptions import DeviceException


class TestPoinTTAPIConnector(unittest.IsolatedAsyncioTestCase):
    """Test suite for PoinTT API connector."""

    def setUp(self):
        self.mock_session = AsyncMock()
        self.device_id = "test_device_123"
        self.access_token = "test_access_token_456"
        self.test_token_file = "test_tokens.json"

    def tearDown(self):
        # Clean up any test files
        if Path(self.test_token_file).exists():
            os.remove(self.test_token_file)

    def test_connector_initialization(self):
        """Test basic connector initialization."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        self.assertEqual(connector._device_id, self.device_id)
        self.assertEqual(connector._access_token, self.access_token)
        self.assertEqual(connector.device_type, POINTTAPI)
        self.assertEqual(connector._token_file, Path(self.test_token_file))

    def test_headers_property(self):
        """Test that headers are correctly formatted."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        headers = connector._headers
        expected_headers = {"Authorization": f"Bearer {self.access_token}"}
        self.assertEqual(headers, expected_headers)

    def test_make_url(self):
        """Test URL construction for different URI formats."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Test with /resource/ prefix (should be stripped)
        url1 = connector._make_url("/resource/airConditioning/temperatureSetpoint")
        expected1 = f"https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways/{self.device_id}/resource/airConditioning/temperatureSetpoint"
        self.assertEqual(url1, expected1)

        # Test without /resource/ prefix
        url2 = connector._make_url("/airConditioning/operationMode")
        expected2 = f"https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways/{self.device_id}/resource/airConditioning/operationMode"
        self.assertEqual(url2, expected2)

    async def test_get_request(self):
        """Test GET request functionality."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_type = "application/json"
        mock_response.json.return_value = {"value": "test_value", "type": "stringValue"}

        # Setup the mock to work with async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        self.mock_session.get.return_value = mock_context

        result = await connector.get("/airConditioning/operationMode")

        self.assertEqual(result, {"value": "test_value", "type": "stringValue"})
        self.mock_session.get.assert_called_once()

    async def test_put_request(self):
        """Test PUT request functionality."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 204

        # Setup the mock to work with async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        self.mock_session.put.return_value = mock_context

        result = await connector.put("/airConditioning/temperatureSetpoint", 22.5)

        self.assertTrue(result)
        self.mock_session.put.assert_called_once()

        # Check that the data was properly formatted
        call_args = self.mock_session.put.call_args
        self.assertIn("data", call_args.kwargs)
        data = json.loads(call_args.kwargs["data"])
        self.assertEqual(data, {"value": 22.5})


class TestTokenManagement(unittest.IsolatedAsyncioTestCase):
    """Test suite for OAuth token management."""

    def setUp(self):
        self.mock_session = AsyncMock()
        self.device_id = "test_device_123"
        self.access_token = "test_access_token_456"
        self.test_token_file = "test_tokens.json"

    def tearDown(self):
        if Path(self.test_token_file).exists():
            os.remove(self.test_token_file)

    def test_save_tokens_creates_secure_file(self):
        """Test that token saving creates a file with secure permissions."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Set up token data
        connector._refresh_token = "test_refresh_token"
        connector._token_expires_at = datetime.now() + timedelta(hours=1)

        connector._save_tokens()

        # Check file was created
        self.assertTrue(Path(self.test_token_file).exists())

        # Check file permissions (should be 0600)
        file_stat = Path(self.test_token_file).stat()
        permissions = oct(file_stat.st_mode)[-3:]
        self.assertEqual(permissions, "600")

        # Check file contents
        with open(self.test_token_file, 'r') as f:
            tokens = json.load(f)
            self.assertEqual(tokens["access_token"], self.access_token)
            self.assertEqual(tokens["refresh_token"], "test_refresh_token")
            self.assertEqual(tokens["device_id"], self.device_id)
            self.assertIn("expires_at", tokens)
            self.assertIn("saved_at", tokens)

    def test_load_tokens_from_file(self):
        """Test loading tokens from existing file."""
        # Create a token file
        tokens = {
            "access_token": "loaded_access_token",
            "refresh_token": "loaded_refresh_token",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "saved_at": datetime.now().isoformat(),
            "device_id": self.device_id
        }

        with open(self.test_token_file, 'w') as f:
            json.dump(tokens, f)

        # Create connector (should load tokens automatically)
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token="original_token",  # This should be overridden
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Verify tokens were loaded
        self.assertEqual(connector._access_token, "loaded_access_token")
        self.assertEqual(connector._refresh_token, "loaded_refresh_token")
        self.assertIsNotNone(connector._token_expires_at)

    def test_token_expiration_check(self):
        """Test token expiration detection."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Test with no expiration time
        self.assertFalse(connector._is_token_expired())

        # Test with expired token
        connector._token_expires_at = datetime.now() - timedelta(minutes=10)
        self.assertTrue(connector._is_token_expired())

        # Test with token expiring soon (within 5 minutes)
        connector._token_expires_at = datetime.now() + timedelta(minutes=2)
        self.assertTrue(connector._is_token_expired())

        # Test with valid token
        connector._token_expires_at = datetime.now() + timedelta(hours=1)
        self.assertFalse(connector._is_token_expired())

    async def test_token_refresh(self):
        """Test automatic token refresh functionality."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Set up expired token
        connector._refresh_token = "test_refresh_token"
        connector._token_expires_at = datetime.now() - timedelta(minutes=10)

        # Mock successful refresh response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }

        self.mock_session.post.return_value.__aenter__.return_value = mock_response

        result = await connector._refresh_access_token()

        self.assertTrue(result)
        self.assertEqual(connector._access_token, "new_access_token")
        self.assertEqual(connector._refresh_token, "new_refresh_token")
        self.assertIsNotNone(connector._token_expires_at)

    def test_oauth_url_generation(self):
        """Test OAuth authorization URL generation."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        auth_url = connector.build_auth_url()

        self.assertIn("singlekey-id.com", auth_url)
        self.assertIn("client_id=762162C0-FA2D-4540-AE66-6489F189FADC", auth_url)
        self.assertIn("response_type=code", auth_url)
        self.assertIn("code_challenge=", auth_url)

    def test_code_extraction(self):
        """Test authorization code extraction from callback URL."""
        connector = PoinTTAPIConnector(
            host=self.device_id,
            access_token=self.access_token,
            loop=self.mock_session,
            token_file=self.test_token_file
        )

        # Test valid callback URL
        callback_url = "com.bosch.tt.dashtt.pointt://app/login?code=test_auth_code_123&state=test_state"
        code = connector.extract_code_from_url(callback_url)
        self.assertEqual(code, "test_auth_code_123")

        # Test URL without code
        invalid_url = "com.bosch.tt.dashtt.pointt://app/login?error=access_denied"
        code = connector.extract_code_from_url(invalid_url)
        self.assertIsNone(code)


class TestPoinTTAPIGateway(unittest.IsolatedAsyncioTestCase):
    """Test suite for PoinTT API Gateway."""

    def setUp(self):
        self.mock_session = AsyncMock()
        self.device_id = "test_device_123"
        self.access_token = "test_access_token_456"
        self.test_token_file = "test_tokens.json"

    def tearDown(self):
        if Path(self.test_token_file).exists():
            os.remove(self.test_token_file)

    def test_gateway_initialization(self):
        """Test PoinTT API Gateway initialization."""
        gateway = PoinTTAPIGateway(
            device_id=self.device_id,
            access_token=self.access_token,
            session=self.mock_session,
            token_file=self.test_token_file
        )

        self.assertEqual(gateway.device_type, POINTTAPI)
        self.assertEqual(gateway._device_id, self.device_id)
        self.assertIsNotNone(gateway._connector)
        self.assertEqual(type(gateway._connector).__name__, "PoinTTAPIConnector")

    @patch('bosch_thermostat_client.gateway.pointtapi.get_initial_db')
    async def test_gateway_device_model_detection(self, mock_get_db):
        """Test device model detection in gateway."""
        mock_get_db.return_value = {
            "models": {
                POINTTAPI: {
                    "value": POINTTAPI,
                    "name": "PoinTT API",
                    "type": POINTTAPI
                }
            }
        }

        gateway = PoinTTAPIGateway(
            device_id=self.device_id,
            access_token=self.access_token,
            session=self.mock_session,
            token_file=self.test_token_file
        )

        db = await mock_get_db.return_value
        device_model = gateway.get_device_model(db)

        expected_model = {
            "value": POINTTAPI,
            "name": "PoinTT API",
            "type": POINTTAPI
        }
        self.assertEqual(device_model, expected_model)


class TestACCircuitTDD(unittest.IsolatedAsyncioTestCase):
    """TDD test cases for Air Conditioning circuit implementation.

    These tests define the expected behavior before implementation.
    """

    def test_ac_circuit_should_exist(self):
        """Test that AC circuit class should be importable."""
        # This should succeed once we implement the AC circuit
        try:
            from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit
            self.assertTrue(True)  # Import succeeded
        except ImportError:
            self.fail("ACCircuit class should be importable")

    def setUp(self):
        """Set up test fixtures for AC circuit tests."""
        self.mock_connector = AsyncMock()
        self.device_id = "test_ac_device"
        self.attr_id = "/airConditioning"
        self.db = {"ac": {}}  # Mock database
        self.bus_type = "test_bus"

        # Mock data structure that ACCircuit will use
        self.mock_data = {
            "/airConditioning/temperatureSetpoint": {"result": {"value": 22.0}},
            "/airConditioning/roomTemperature": {"result": {"value": 20.5}},
            "/airConditioning/operationMode": {"result": {"value": "cool"}},
            "/airConditioning/fanSpeed": {"result": {"value": "auto"}},
            "/airConditioning/airFlowHorizontal": {"result": {"value": "center"}},
            "/airConditioning/airFlowVertical": {"result": {"value": "auto"}},
            "/airConditioning/acControl": {"result": {"value": "on"}},
        }

    def test_ac_circuit_temperature_control(self):
        """Test that AC circuit should support temperature control."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Manually set up mock data in circuit._data
        circuit._data = self.mock_data

        # Test temperature setpoint property access
        self.assertEqual(circuit.target_temperature, 22.0)

        # Test current temperature property access
        self.assertEqual(circuit.current_temp, 20.5)

    async def test_ac_circuit_set_temperature(self):
        """Test setting temperature on AC circuit."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Mock successful response
        self.mock_connector.put.return_value = True

        # Test valid temperature setting
        result = await circuit.set_temperature(22.5)
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/temperatureSetpoint", 22.5)

        # Test invalid temperature (out of range)
        result = await circuit.set_temperature(50.0)
        self.assertFalse(result)

        # Test invalid temperature (not a number)
        result = await circuit.set_temperature("invalid")
        self.assertFalse(result)

    def test_ac_circuit_operation_modes(self):
        """Test that AC circuit should support operation mode switching."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Manually set up mock data in circuit._data
        circuit._data = self.mock_data

        # Test available modes
        expected_modes = ["auto", "heat", "cool", "fanOnly"]
        self.assertEqual(circuit.available_operation_modes, expected_modes)

        # Test operation mode property access
        self.assertEqual(circuit.operation_mode, "cool")

    async def test_ac_circuit_set_operation_mode(self):
        """Test setting operation mode on AC circuit."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Mock successful response
        self.mock_connector.put.return_value = True

        # Test valid mode setting
        result = await circuit.set_operation_mode("cool")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/operationMode", "cool")

        # Test invalid mode
        result = await circuit.set_operation_mode("invalid_mode")
        self.assertFalse(result)

    def test_ac_circuit_fan_speed_control(self):
        """Test that AC circuit should support fan speed control."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Manually set up mock data in circuit._data
        circuit._data = self.mock_data

        # Test available fan speeds
        expected_speeds = ["auto", "quiet", "low", "mid", "high"]
        self.assertEqual(circuit.available_fan_speeds, expected_speeds)

        # Test fan speed property access
        self.assertEqual(circuit.fan_speed, "auto")

    async def test_ac_circuit_set_fan_speed(self):
        """Test setting fan speed on AC circuit."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Mock successful response
        self.mock_connector.put.return_value = True

        # Test valid fan speed setting
        result = await circuit.set_fan_speed("high")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/fanSpeed", "high")

        # Test invalid fan speed
        result = await circuit.set_fan_speed("invalid_speed")
        self.assertFalse(result)

    def test_ac_circuit_air_flow_control(self):
        """Test that AC circuit should support air flow direction control."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Manually set up mock data in circuit._data
        circuit._data = self.mock_data

        # Test available horizontal air flows
        expected_horizontal = ["center", "left", "right", "swing"]
        self.assertEqual(circuit.available_horizontal_airflows, expected_horizontal)

        # Test available vertical air flows
        expected_vertical = ["auto", "angle1", "angle2", "angle3", "angle4", "angle5", "swing"]
        self.assertEqual(circuit.available_vertical_airflows, expected_vertical)

        # Test air flow properties
        self.assertEqual(circuit.air_flow_horizontal, "center")
        self.assertEqual(circuit.air_flow_vertical, "auto")

    async def test_ac_circuit_set_air_flow(self):
        """Test setting air flow directions on AC circuit."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Mock successful response
        self.mock_connector.put.return_value = True

        # Test horizontal air flow setting
        result = await circuit.set_air_flow_horizontal("swing")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/airFlowHorizontal", "swing")

        # Test vertical air flow setting
        result = await circuit.set_air_flow_vertical("angle3")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/airFlowVertical", "angle3")

        # Test invalid directions
        result = await circuit.set_air_flow_horizontal("invalid")
        self.assertFalse(result)

        result = await circuit.set_air_flow_vertical("invalid")
        self.assertFalse(result)

    def test_ac_circuit_hvac_action(self):
        """Test HVAC action detection based on mode and state."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit
        from bosch_thermostat_client.const import HVAC_HEAT, HVAC_COOL, HVAC_FAN, HVAC_OFF

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Test that hvac_action property exists
        self.assertIsNotNone(circuit.hvac_action)

    async def test_ac_circuit_power_control(self):
        """Test turning AC on/off."""
        from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit

        circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id=self.attr_id,
            db=self.db,
            _type="ac",
            bus_type=self.bus_type
        )

        # Mock successful response
        self.mock_connector.put.return_value = True

        # Test turning on
        result = await circuit.turn_on()
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/acControl", "on")

        # Test turning off
        result = await circuit.turn_off()
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/acControl", "off")


if __name__ == "__main__":
    unittest.main()