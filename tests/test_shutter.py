"""Define tests for shutter module."""

import json
from unittest.mock import AsyncMock, patch

import anyio

from pyatmo import DeviceType
from tests.common import MockResponse


async def test_async_shutter_NBR(async_home):
    """Test NLP Bubendorf iDiamant roller shutter."""
    module_id = "0009999992"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBR
    assert module.firmware_revision == 16
    assert module.current_position == 0


async def test_async_shutter_Z3V(async_home):
    """Test NLG Legrand roller shutter 3rd party."""
    module_id = "12:34:56:80:00:c3:69:3d"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.Z3V
    assert module.firmware_revision == 16
    assert module.current_position == 0


async def test_async_shutter_NBO(async_home):
    """Test NBO Bubendorf iDiamant roller shutter."""
    module_id = "0009999993"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBO
    assert module.firmware_revision == 22
    assert module.current_position == 0


async def test_async_shutters(async_home):
    """Test basic shutter functionality."""
    room_id = "3688132631"
    assert room_id in async_home.rooms

    module_id = "0009999992"
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBR

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

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
