"""Define tests for shutter module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from pyatmo import DeviceType
from tests.common import MockResponse

# pylint: disable=F6401


@pytest.mark.asyncio()
async def test_async_shutter_NBR(async_home):  # pylint: disable=invalid-name
    """Test NLP Bubendorf iDiamant roller shutter."""
    module_id = "0009999992"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBR
    assert module.firmware_revision == 16
    assert module.current_position == 0


@pytest.mark.asyncio()
async def test_async_shutter_NBO(async_home):  # pylint: disable=invalid-name
    """Test NBO Bubendorf iDiamant roller shutter."""
    module_id = "0009999993"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBO
    assert module.firmware_revision == 22
    assert module.current_position == 0


@pytest.mark.asyncio()
async def test_async_shutters(async_home):
    """Test basic shutter functionality."""
    room_id = "3688132631"
    assert room_id in async_home.rooms

    module_id = "0009999992"
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBR

    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    def gen_json_data(position):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "bridge": "12:34:56:30:d5:d4",
                            "id": module_id,
                            "target_position": position,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_open()
        mock_resp.assert_awaited_with(
            params=gen_json_data(100),
            endpoint="api/setstate",
        )

        assert await module.async_close()
        mock_resp.assert_awaited_with(
            params=gen_json_data(0),
            endpoint="api/setstate",
        )

        assert await module.async_stop()
        mock_resp.assert_awaited_with(
            params=gen_json_data(-1),
            endpoint="api/setstate",
        )

        assert await module.async_move_to_preferred_position()
        mock_resp.assert_awaited_with(
            params=gen_json_data(-2),
            endpoint="api/setstate",
        )

        assert await module.async_set_target_position(47)
        mock_resp.assert_awaited_with(
            params=gen_json_data(47),
            endpoint="api/setstate",
        )

        assert await module.async_set_target_position(-10)
        mock_resp.assert_awaited_with(
            params=gen_json_data(-1),
            endpoint="api/setstate",
        )

        assert await module.async_set_target_position(101)
        mock_resp.assert_awaited_with(
            params=gen_json_data(100),
            endpoint="api/setstate",
        )
