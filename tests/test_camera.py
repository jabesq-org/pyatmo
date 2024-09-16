"""Define tests for camera module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from pyatmo import DeviceType
from tests.common import MockResponse

# pylint: disable=F6401


@pytest.mark.asyncio()
async def test_async_camera_NACamera(async_home):  # pylint: disable=invalid-name
    """Test Netatmo indoor camera module."""
    module_id = "12:34:56:00:f1:62"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    await module.async_update_camera_urls()
    assert module.device_type == DeviceType.NACamera
    assert module.is_local
    assert module.local_url == "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    person_id = "91827374-7e04-5298-83ad-a0cb8372dff1"
    assert person_id in module.home.persons
    person = module.home.persons[person_id]
    assert person.pseudo == "John Doe"
    assert person.out_of_sight
    assert person.last_seen == 1557071156


@pytest.mark.asyncio()
async def test_async_NOC(async_home):  # pylint: disable=invalid-name
    """Test basic outdoor camera functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC
    assert module.firmware_revision == 3002000
    assert module.firmware_name == "3.2.0"
    assert module.monitoring is True
    assert module.alim_status == 2
    assert module.is_local is False
    assert module.floodlight == "auto"

    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    def gen_json_data(state):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": module_id,
                            "floodlight": state,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_floodlight_on()
        mock_resp.assert_awaited_with(
            params=gen_json_data("on"),
            endpoint="api/setstate",
        )

        assert await module.async_floodlight_off()
        mock_resp.assert_awaited_with(
            params=gen_json_data("off"),
            endpoint="api/setstate",
        )

        assert await module.async_floodlight_auto()
        mock_resp.assert_awaited_with(
            params=gen_json_data("auto"),
            endpoint="api/setstate",
        )


@pytest.mark.asyncio()
async def test_async_camera_monitoring(async_home):
    """Test basic camera monitoring functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC
    assert module.is_local is False

    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    def gen_json_data(state):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": module_id,
                            "monitoring": state,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_monitoring_on()
        mock_resp.assert_awaited_with(
            params=gen_json_data("on"),
            endpoint="api/setstate",
        )

        assert await module.async_monitoring_off()
        mock_resp.assert_awaited_with(
            params=gen_json_data("off"),
            endpoint="api/setstate",
        )
