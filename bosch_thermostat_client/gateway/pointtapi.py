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
)
from bosch_thermostat_client.const.ivt import SYSTEM_INFO
from bosch_thermostat_client.const.pointtapi import CIRCUIT_TYPES
from bosch_thermostat_client.exceptions import DeviceException

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
        await super().initialize()
        # Set up bulk endpoints for efficient API requests
        bulk_endpoints = self._db.get("bulk_endpoints", {})
        for endpoint, uris in bulk_endpoints.items():
            self._connector.add_bulk_endpoint(endpoint, uris)

    def get_device_model(self, _db):
        """Find device model."""
        # Device model is not provided by PoinTTAPI
        return _db.get(MODELS).get(POINTTAPI)
