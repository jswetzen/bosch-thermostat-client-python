"""Gateway module connecting to Bosch thermostat."""

import json
from urllib.parse import urljoin
import logging
from contextlib import asynccontextmanager

from bosch_thermostat_client.connectors import connector_ivt_chooser
from bosch_thermostat_client.const import (
    DHW,
    EMS,
    GATEWAY,
    HC,
    MODELS,
    POINTTAPI,
    SENSORS,
    SYSTEM_BUS,
    VALUE,
    VALUES,
)
from bosch_thermostat_client.const.ivt import CAN, IVT_MBLAN, SYSTEM_INFO
from bosch_thermostat_client.encryption import IVTEncryption as Encryption
from bosch_thermostat_client.exceptions import DeviceException

from .base import BaseGateway

_LOGGER = logging.getLogger(__name__)

POINTTAPI_BASE_URL = (
    "https://pointt-api.bosch-thermotechnology.com/pointt-api/api/v1/gateways/"
)


class BulkEndpoint:
    """Stores a list of URIs for bulk requests.
    Keeps track of requesting the bulk data, and storing the result
    for each URI. When a URI is requested and there is data available,
    no new bulk request is made unless it is the second time that URI
    is requested since the last bulk request.
    """

    def __init__(self, loop, headers, endpoint, uris):
        self._loop = loop
        self._headers = headers
        self._endpoint = endpoint
        self._uris = uris
        self._data = {}
        self._requested_uris = set()

    async def get(self, uri):
        if uri in self._uris:
            if uri not in self._data or uri in self._requested_uris:
                await self._request()
                self._requested_uris.clear()
            self._requested_uris.add(uri)
            return self._data.get(uri)
        else:
            return {}

    async def _request(self):
        async with self._loop.get(self._endpoint, headers=self._headers) as response:
            data = await response.json()
        for uri_data in data.get("references", []):
            self._data[uri_data["id"]] = uri_data


class PoinTTAPIConnector:
    def __init__(self, loop, device_id, access_token, device_type=POINTTAPI):
        self._loop = loop
        self._base_url = f"{POINTTAPI_BASE_URL}{device_id}/"
        self._access_token = f"Bearer {access_token}"
        self._bulk_endpoints = {}
        self._uri_bulk_endpoints = {}
        self.device_type = device_type

    @property
    def _headers(self):
        return {"Authorization": self._access_token}

    def _make_url(self, uri):
        return urljoin(self._base_url, uri.lstrip("/"))

    def add_bulk_endpoint(self, endpoint, uris):
        bulk_endpoint = BulkEndpoint(
            self._loop, self._headers, self._make_url(endpoint), uris
        )
        self._bulk_endpoints[endpoint] = bulk_endpoint
        self._uri_bulk_endpoints.update({uri: bulk_endpoint for uri in uris})

    @asynccontextmanager
    async def request(self, method, uri, data=None):
        url = self._make_url(uri)
        headers = {
            "Authorization": self._access_token,
        }
        method = getattr(self._loop, method)
        async with method(url, headers=headers, data=data) as response:
            yield response

    async def get(self, uri):
        if uri in self._uri_bulk_endpoints:
            return await self._uri_bulk_endpoints[uri].get(uri)
        async with self.request("get", uri) as response:
            return await response.json()

    async def put(self, uri, data):
        # TODO: Will have to add /resource/
        url = self._make_url(uri)
        headers = {
            "Authorization": self._access_token,
            "Content-Type": "application/json",
        }
        async with self._loop.put(
            self._make_url(uri), headers={"Authorization": self._access_token}
        ) as response:
            return await response.json()


class PoinTTAPIGateway(BaseGateway):
    """Gateway connecting to the closed Bosch Pointt API."""

    device_type = POINTTAPI
    circuit_types = {}

    def __init__(
        self,
        device_id,
        access_token,
        session=None,
    ):
        """IVT Gateway constructor

        Args:
            session (loop): loop or websession
            session_type (str): either HTTP or XMPP
            host (str): host IP or hostname for HTTP or serial number for XMPP
            access_key (str): access key to Bosch Gateway
            password (str, optional): Password to Bosch Gateway. Defaults to None.
        """
        self._host = f"{POINTTAPI_BASE_URL}{device_id}/resource/"
        self._device_id = device_id
        self._access_token = access_token
        self._connector = PoinTTAPIConnector(
            loop=session,
            device_id=self._device_id,
            access_token=self._access_token,
        )
        self._data = {GATEWAY: {}, HC: None, SENSORS: None}
        super().__init__(POINTTAPI_BASE_URL)

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
        bulk_endpoints = self._db.get("bulk_endpoints", {}).items()
        for endpoint, uris in bulk_endpoints:
            self._connector.add_bulk_endpoint(endpoint, uris)

    def get_device_model(self, _db):
        """Find device model."""
        # Device model is not provided by PoinTTAPI
        return _db.get(MODELS).get(POINTTAPI)
