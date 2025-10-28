"""Integration test demonstrating AC circuit usage."""

import unittest
import asyncio
from unittest.mock import AsyncMock
from bosch_thermostat_client.circuits.pointtapi.ac import ACCircuit
from bosch_thermostat_client.const import HVAC_COOL, HVAC_HEAT, HVAC_FAN, HVAC_OFF


class TestACCircuitIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test for AC circuit functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_connector = AsyncMock()
        self.mock_connector.put.return_value = True

        # Create AC circuit
        self.circuit = ACCircuit(
            connector=self.mock_connector,
            attr_id="/airConditioning",
            db={"ac": {}},
            _type="ac",
            bus_type="test_bus"
        )

        # Set up realistic mock data
        self.circuit._data = {
            "/airConditioning/temperatureSetpoint": {"result": {"value": 24.0}},
            "/airConditioning/roomTemperature": {"result": {"value": 26.0}},
            "/airConditioning/operationMode": {"result": {"value": "cool"}},
            "/airConditioning/fanSpeed": {"result": {"value": "mid"}},
            "/airConditioning/airFlowHorizontal": {"result": {"value": "swing"}},
            "/airConditioning/airFlowVertical": {"result": {"value": "angle3"}},
            "/airConditioning/acControl": {"result": {"value": "on"}},
        }

    async def test_full_ac_control_scenario(self):
        """Test a complete AC control scenario."""
        # 1. Check current status
        self.assertEqual(self.circuit.current_temp, 26.0)
        self.assertEqual(self.circuit.target_temperature, 24.0)
        self.assertEqual(self.circuit.operation_mode, "cool")
        self.assertTrue(self.circuit.is_on)
        self.assertEqual(self.circuit.hvac_action, HVAC_COOL)

        # 2. Adjust temperature
        result = await self.circuit.set_temperature(22.0)
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/temperatureSetpoint", 22.0)

        # 3. Change operation mode to heating
        result = await self.circuit.set_operation_mode("heat")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/operationMode", "heat")

        # 4. Adjust fan speed for comfort
        result = await self.circuit.set_fan_speed("high")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/fanSpeed", "high")

        # 5. Set air flow for better distribution
        result = await self.circuit.set_air_flow_horizontal("center")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/airFlowHorizontal", "center")

        result = await self.circuit.set_air_flow_vertical("auto")
        self.assertTrue(result)
        self.mock_connector.put.assert_called_with("/airConditioning/airFlowVertical", "auto")

    async def test_hvac_action_logic(self):
        """Test HVAC action determination in different scenarios."""
        # Test cooling mode when room is warmer than setpoint
        self.circuit._data["/airConditioning/operationMode"]["result"]["value"] = "cool"
        self.circuit._data["/airConditioning/roomTemperature"]["result"]["value"] = 26.0
        self.circuit._data["/airConditioning/temperatureSetpoint"]["result"]["value"] = 22.0
        self.assertEqual(self.circuit.hvac_action, HVAC_COOL)

        # Test heating mode when room is cooler than setpoint
        self.circuit._data["/airConditioning/operationMode"]["result"]["value"] = "heat"
        self.circuit._data["/airConditioning/roomTemperature"]["result"]["value"] = 18.0
        self.circuit._data["/airConditioning/temperatureSetpoint"]["result"]["value"] = 22.0
        self.assertEqual(self.circuit.hvac_action, HVAC_HEAT)

        # Test fan-only mode
        self.circuit._data["/airConditioning/operationMode"]["result"]["value"] = "fanOnly"
        self.assertEqual(self.circuit.hvac_action, HVAC_FAN)

        # Test AC off
        self.circuit._data["/airConditioning/acControl"]["result"]["value"] = "off"
        self.assertEqual(self.circuit.hvac_action, HVAC_OFF)

    async def test_error_handling(self):
        """Test error handling in AC circuit methods."""
        # Test connector failure
        self.mock_connector.put.return_value = False

        result = await self.circuit.set_temperature(20.0)
        self.assertFalse(result)

        result = await self.circuit.set_operation_mode("auto")
        self.assertFalse(result)

        # Test connector exception
        self.mock_connector.put.side_effect = Exception("Connection failed")

        result = await self.circuit.set_fan_speed("low")
        self.assertFalse(result)

    def test_available_options(self):
        """Test that all available options are correctly defined."""
        # Operation modes should match PoinTT API specification
        self.assertEqual(
            self.circuit.available_operation_modes,
            ["auto", "heat", "cool", "fanOnly"]
        )

        # Fan speeds should match PoinTT API specification
        self.assertEqual(
            self.circuit.available_fan_speeds,
            ["auto", "quiet", "low", "mid", "high"]
        )

        # Air flow options should match PoinTT API specification
        self.assertEqual(
            self.circuit.available_horizontal_airflows,
            ["center", "left", "right", "swing"]
        )

        self.assertEqual(
            self.circuit.available_vertical_airflows,
            ["auto", "angle1", "angle2", "angle3", "angle4", "angle5", "swing"]
        )


if __name__ == "__main__":
    unittest.main()