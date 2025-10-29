"""Air Conditioning Circuit for PoinTT API."""

import logging
from ..circuit import BasicCircuit
from bosch_thermostat_client.const import (
    VALUE,
    URI,
    RESULT,
    HVAC_COOL,
    HVAC_HEAT,
    HVAC_FAN,
    HVAC_OFF,
)

_LOGGER = logging.getLogger(__name__)


class ACCircuit(BasicCircuit):
    """Air Conditioning circuit for PoinTT API devices."""

    # AC-specific operation modes
    AC_MODE_AUTO = "auto"
    AC_MODE_HEAT = "heat"
    AC_MODE_COOL = "cool"
    AC_MODE_FAN = "fanOnly"

    # Fan speeds
    FAN_AUTO = "auto"
    FAN_QUIET = "quiet"
    FAN_LOW = "low"
    FAN_MID = "mid"
    FAN_HIGH = "high"

    # Air flow directions
    AIRFLOW_H_CENTER = "center"
    AIRFLOW_H_LEFT = "left"
    AIRFLOW_H_RIGHT = "right"
    AIRFLOW_H_SWING = "swing"

    AIRFLOW_V_AUTO = "auto"
    AIRFLOW_V_ANGLE1 = "angle1"
    AIRFLOW_V_ANGLE2 = "angle2"
    AIRFLOW_V_ANGLE3 = "angle3"
    AIRFLOW_V_ANGLE4 = "angle4"
    AIRFLOW_V_ANGLE5 = "angle5"
    AIRFLOW_V_SWING = "swing"

    def __init__(self, connector, attr_id, db, _type, bus_type, **kwargs):
        """Initialize AC circuit."""
        super().__init__(connector, attr_id, db, _type, bus_type, **kwargs)

        # AC-specific URIs based on PoinTT API schema
        self._operation_mode_uri = "/airConditioning/operationMode"
        self._ac_control_uri = "/airConditioning/acControl"
        self._temperature_setpoint_uri = "/airConditioning/temperatureSetpoint"
        self._room_temperature_uri = "/airConditioning/roomTemperature"
        self._fan_speed_uri = "/airConditioning/fanSpeed"
        self._airflow_horizontal_uri = "/airConditioning/airFlowHorizontal"
        self._airflow_vertical_uri = "/airConditioning/airFlowVertical"

    async def initialize(self):
        """Initialize AC circuit.

        PoinTT API doesn't have individual circuit endpoints - all data comes from
        the bulk endpoint. We just mark the circuit as active and initialize switches.
        """
        # Mark circuit as active (no STATUS endpoint to fetch)
        self._state = True
        # Initialize switches if database has them
        from bosch_thermostat_client.const import SWITCHES
        await self._switches.initialize(switches=self._db.get(SWITCHES))

    @property
    def current_temp(self):
        """Get current room temperature."""
        try:
            return self.get_value(self._room_temperature_uri)
        except (KeyError, AttributeError):
            return None

    @property
    def target_temperature(self):
        """Get target temperature setpoint."""
        try:
            return self.get_value(self._temperature_setpoint_uri)
        except (KeyError, AttributeError):
            return None

    @property
    def operation_mode(self):
        """Get current operation mode."""
        try:
            return self.get_value(self._operation_mode_uri)
        except (KeyError, AttributeError):
            return None

    @property
    def fan_speed(self):
        """Get current fan speed."""
        try:
            return self.get_value(self._fan_speed_uri)
        except (KeyError, AttributeError):
            return None

    @property
    def air_flow_horizontal(self):
        """Get horizontal air flow direction."""
        try:
            return self.get_value(self._airflow_horizontal_uri)
        except (KeyError, AttributeError):
            return None

    @property
    def air_flow_vertical(self):
        """Get vertical air flow direction."""
        try:
            return self.get_value(self._airflow_vertical_uri)
        except (KeyError, AttributeError):
            return None

    @property
    def is_on(self):
        """Check if AC is turned on."""
        try:
            ac_control = self.get_value(self._ac_control_uri)
            return ac_control == "on"
        except (KeyError, AttributeError):
            return False

    @property
    def hvac_action(self):
        """Get current HVAC action based on operation mode and state."""
        if not self.is_on:
            return HVAC_OFF

        mode = self.operation_mode
        if mode == self.AC_MODE_HEAT:
            return HVAC_HEAT
        elif mode == self.AC_MODE_COOL:
            return HVAC_COOL
        elif mode == self.AC_MODE_FAN:
            return HVAC_FAN
        elif mode == self.AC_MODE_AUTO:
            # In auto mode, determine action based on current vs target temp
            current = self.current_temp
            target = self.target_temperature
            if current and target:
                if current < target:
                    return HVAC_HEAT
                elif current > target:
                    return HVAC_COOL
                else:
                    return HVAC_FAN
        return HVAC_OFF

    @property
    def available_operation_modes(self):
        """Get available operation modes."""
        return [self.AC_MODE_AUTO, self.AC_MODE_HEAT, self.AC_MODE_COOL, self.AC_MODE_FAN]

    @property
    def available_fan_speeds(self):
        """Get available fan speeds."""
        return [self.FAN_AUTO, self.FAN_QUIET, self.FAN_LOW, self.FAN_MID, self.FAN_HIGH]

    @property
    def available_horizontal_airflows(self):
        """Get available horizontal air flow directions."""
        return [self.AIRFLOW_H_CENTER, self.AIRFLOW_H_LEFT, self.AIRFLOW_H_RIGHT, self.AIRFLOW_H_SWING]

    @property
    def available_vertical_airflows(self):
        """Get available vertical air flow directions."""
        return [self.AIRFLOW_V_AUTO, self.AIRFLOW_V_ANGLE1, self.AIRFLOW_V_ANGLE2,
                self.AIRFLOW_V_ANGLE3, self.AIRFLOW_V_ANGLE4, self.AIRFLOW_V_ANGLE5,
                self.AIRFLOW_V_SWING]

    async def set_temperature(self, temperature):
        """Set target temperature."""
        if not isinstance(temperature, (int, float)):
            _LOGGER.error("Temperature must be a number")
            return False

        # PoinTT API temperature range is 16.0 - 30.0°C
        if not (16.0 <= temperature <= 30.0):
            _LOGGER.error("Temperature must be between 16.0 and 30.0°C")
            return False

        try:
            result = await self._connector.put(self._temperature_setpoint_uri, temperature)
            if result:
                _LOGGER.debug("Set temperature to %s°C", temperature)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to set temperature: %s", e)
            return False

    async def set_operation_mode(self, mode):
        """Set operation mode (auto, heat, cool, fanOnly)."""
        if mode not in self.available_operation_modes:
            _LOGGER.error("Invalid operation mode: %s", mode)
            return False

        try:
            result = await self._connector.put(self._operation_mode_uri, mode)
            if result:
                _LOGGER.debug("Set operation mode to %s", mode)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to set operation mode: %s", e)
            return False

    async def set_fan_speed(self, speed):
        """Set fan speed (auto, quiet, low, mid, high)."""
        if speed not in self.available_fan_speeds:
            _LOGGER.error("Invalid fan speed: %s", speed)
            return False

        try:
            result = await self._connector.put(self._fan_speed_uri, speed)
            if result:
                _LOGGER.debug("Set fan speed to %s", speed)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to set fan speed: %s", e)
            return False

    async def set_air_flow_horizontal(self, direction):
        """Set horizontal air flow direction."""
        if direction not in self.available_horizontal_airflows:
            _LOGGER.error("Invalid horizontal air flow direction: %s", direction)
            return False

        try:
            result = await self._connector.put(self._airflow_horizontal_uri, direction)
            if result:
                _LOGGER.debug("Set horizontal air flow to %s", direction)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to set horizontal air flow: %s", e)
            return False

    async def set_air_flow_vertical(self, direction):
        """Set vertical air flow direction."""
        if direction not in self.available_vertical_airflows:
            _LOGGER.error("Invalid vertical air flow direction: %s", direction)
            return False

        try:
            result = await self._connector.put(self._airflow_vertical_uri, direction)
            if result:
                _LOGGER.debug("Set vertical air flow to %s", direction)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to set vertical air flow: %s", e)
            return False

    async def turn_on(self):
        """Turn the AC on."""
        try:
            result = await self._connector.put(self._ac_control_uri, "on")
            if result:
                _LOGGER.debug("Turned AC on")
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to turn AC on: %s", e)
            return False

    async def turn_off(self):
        """Turn the AC off."""
        try:
            result = await self._connector.put(self._ac_control_uri, "off")
            if result:
                _LOGGER.debug("Turned AC off")
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to turn AC off: %s", e)
            return False