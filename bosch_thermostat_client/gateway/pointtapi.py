"""Gateway module connecting to Bosch thermostat via PoinTT API."""

import logging

from bosch_thermostat_client.connectors import connector_ivt_chooser
from bosch_thermostat_client.const import (
    GATEWAY,
    HC,
    AC,
    MODELS,
    POINTTAPI,
    SENSORS,
    VALUE,
    VALUES,
    FIRMWARE_VERSION,
    TYPE,
)
from bosch_thermostat_client.const.ivt import SYSTEM_INFO
from bosch_thermostat_client.const.pointtapi import CIRCUIT_TYPES
from bosch_thermostat_client.exceptions import DeviceException, FirmwareException, UnknownDevice
from bosch_thermostat_client.db import get_db_of_firmware, async_get_errors

from .base import BaseGateway

_LOGGER = logging.getLogger(__name__)


class PoinTTAPIGateway(BaseGateway):
    """Gateway connecting to the Bosch PoinTT API."""

    device_type = POINTTAPI
    circuit_types = CIRCUIT_TYPES

    def __init__(
        self,
        device_id,
        access_token,
        session=None,
        token_file="tokens.json",
    ):
        """PoinTT API Gateway constructor

        Args:
            device_id (str): Device ID for the PoinTT API
            access_token (str): OAuth access token
            session: HTTP session for API requests
            token_file (str): Path to token storage file
        """
        self._device_id = device_id
        self._access_token = access_token

        # Use the connector chooser to get the right connector
        Connector = connector_ivt_chooser(POINTTAPI)
        self._connector = Connector(
            host=device_id,  # For PoinTT API, host is the device ID
            access_token=access_token,
            loop=session,
            token_file=token_file,
        )
        self._data = {GATEWAY: {}, AC: None, SENSORS: None}
        super().__init__(device_id)

    async def _update_info(self, initial_db):
        """Update gateway info from Bosch device."""
        for name, uri in initial_db.items():
            try:
                response = await self._connector.get(uri)
                if VALUE in response:
                    self._data[GATEWAY][name] = response[VALUE]
                elif name == SYSTEM_INFO:
                    self._data[GATEWAY][SYSTEM_INFO] = response.get(VALUES, [])
            except DeviceException as err:
                _LOGGER.debug("Can't fetch data for update_info %s", err)
                pass

    async def initialize(self):
        """Initialize gateway with hardcoded firmware version.

        PoinTT API doesn't expose firmware version endpoint, so we hardcode it.
        """
        # Get base database
        initial_db = await self.get_base_db()

        # Try to fetch gateway info (will skip inaccessible endpoints)
        await self._update_info(initial_db.get(GATEWAY))

        # Hardcode firmware version since PoinTT API doesn't expose it
        self._firmware_version = "05.00.06"
        self._data[GATEWAY][FIRMWARE_VERSION] = self._firmware_version
        _LOGGER.debug("Using hardcoded firmware version: %s", self._firmware_version)

        # Get device model
        self._device = self.get_device_model(initial_db)

        if self._device and VALUE in self._device:
            _LOGGER.debug("Found device %s", self._device)

            # Load firmware-specific database
            self._db = await get_db_of_firmware(
                self._device[TYPE], self._firmware_version
            )

            if self._db:
                _LOGGER.debug(
                    f"Loading database: {self._device[TYPE]} for firmware {self._firmware_version}"
                )
                initial_db.pop(MODELS, None)
                self._db.update(initial_db)
                self._errors = await async_get_errors(self.device_type)

                # Set up bulk endpoints for efficient API requests
                bulk_endpoints = self._db.get("bulk_endpoints", {})
                for endpoint, uris in bulk_endpoints.items():
                    self._connector.add_bulk_endpoint(endpoint, uris)

                self._initialized = True
                return

            raise FirmwareException(
                "You might have unsupported firmware version %s"
                % self._firmware_version
            )

        raise UnknownDevice("Your device is unknown %s" % self._device)

    def get_device_model(self, _db):
        """Find device model."""
        # Device model is not provided by PoinTTAPI, use static value
        # Set bus_type to POINTTAPI for proper circuit initialization
        self._bus_type = POINTTAPI
        return _db.get(MODELS).get(POINTTAPI)
