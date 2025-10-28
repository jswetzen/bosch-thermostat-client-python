import unittest

from unittest.mock import AsyncMock
from bosch_thermostat_client.gateway.pointtapi import BulkEndpoint


class TestBulkEndpoint(unittest.IsolatedAsyncioTestCase):

    URI1 = "/ac/uri1"
    URI2 = "/ac/uri2"
    URI3 = "/ac/uri3"
    TEST_ENDPOINT = "/test_endpoint"

    def setUp(self):
        self.connector = AsyncMock()
        self.endpoint = self.TEST_ENDPOINT
        self.uris = [self.URI1, self.URI2, self.URI3]
        self.bulk_endpoint = BulkEndpoint(self.connector, self.endpoint, self.uris)

    async def test_bulk_endpoint_initial_request(self):
        self.connector.get.return_value = {
            "id": "/test_endpoint",
            "type": "bulk",
            "references": [
                {
                    "id": self.URI1,
                    "type": "stringValue",
                    "value": "value1",
                },
                {
                    "id": self.URI2,
                    "type": "stringValue",
                    "value": "value2",
                },
                {
                    "id": self.URI3,
                    "type": "stringValue",
                    "value": "value3",
                },
            ],
        }
        result = await self.bulk_endpoint.get(self.URI1)
        self.assertEqual(
            result, {"id": self.URI1, "type": "stringValue", "value": "value1"}
        )
        self.connector.get.assert_called_once_with(self.TEST_ENDPOINT)

    async def test_bulk_endpoint_subsequent_request(self):
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "/test_endpoint",
            "type": "bulk",
            "references": [
                {
                    "id": self.URI1,
                    "type": "stringValue",
                    "value": "value1",
                },
                {
                    "id": self.URI2,
                    "type": "stringValue",
                    "value": "value2",
                },
                {
                    "id": self.URI3,
                    "type": "stringValue",
                    "value": "value3",
                },
            ],
        }
        self.mock_session.get.return_value.__aenter__.return_value = mock_response

        result1 = await self.bulk_endpoint.get(self.URI1)
        result2 = await self.bulk_endpoint.get(self.URI2)
        self.assertEqual(
            result1, {"id": self.URI1, "type": "stringValue", "value": "value1"}
        )
        self.assertEqual(
            result2, {"id": self.URI2, "type": "stringValue", "value": "value2"}
        )
        self.mock_session.get.assert_called_once_with(self.TEST_ENDPOINT, headers=self.headers)

    async def test_bulk_endpoint_request_not_in_data(self):
        self.connector.get.return_value = {
            "id": "/test_endpoint",
            "type": "bulk",
            "references": [
                {
                    "id": self.URI1,
                    "type": "stringValue",
                    "value": "value1",
                },
                {
                    "id": self.URI2,
                    "type": "stringValue",
                    "value": "value2",
                },
                {
                    "id": self.URI3,
                    "type": "stringValue",
                    "value": "value3",
                },
            ],
        }
        result = await self.bulk_endpoint.get("/ac/not_in_data")
        self.assertEqual(result, {})

    async def test_bulk_endpoint_refetch_request(self):
        self.connector.get.return_value = {
            "id": "/test_endpoint",
            "type": "bulk",
            "references": [
                {
                    "id": self.URI1,
                    "type": "stringValue",
                    "value": "value1",
                },
                {
                    "id": self.URI2,
                    "type": "stringValue",
                    "value": "value2",
                },
            ],
        }
        result1 = await self.bulk_endpoint.get(self.URI1)
        result2 = await self.bulk_endpoint.get(self.URI2)
        self.connector.get.assert_called_once_with(self.TEST_ENDPOINT)
        result2 = await self.bulk_endpoint.get(self.URI2)
        self.assertEqual(self.connector.get.call_count, 2)
        self.assertEqual(
            result1, {"id": self.URI1, "type": "stringValue", "value": "value1"}
        )
        self.assertEqual(
            result2, {"id": self.URI2, "type": "stringValue", "value": "value2"}
        )


if __name__ == "__main__":
    unittest.main()
