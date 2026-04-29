"""Define tests for VELUX ACTIVE modules."""

import json
from unittest.mock import AsyncMock, patch

import pyatmo
from pyatmo import DeviceType
from pyatmo.modules.device_types import DeviceCategory
from tests.common import MockResponse, load_fixture


async def test_async_velux_modules(async_auth):
    """Test VELUX gateway and cover parsing."""
    homesdata = json.loads(load_fixture("homesdata_velux.json"))
    homestatus = json.loads(load_fixture("homestatus_velux_home_id.json"))
    homestatus["body"]["home"]["modules"][0]["name"] = "VELUX gateway"
    homestatus["body"]["home"]["modules"][0]["reachable"] = False

    account = pyatmo.AsyncAccount(async_auth)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(
            side_effect=[
                MockResponse(homesdata, 200),
                MockResponse(homestatus, 200),
            ],
        ),
    ):
        await account.async_update_topology()
        await account.async_update_status("velux_home_id")

    home = account.homes["velux_home_id"]
    assert home.name == "VELUX Test Home"

    gateway = home.modules["velux_gateway_id"]
    assert gateway.device_type == DeviceType.NXG
    assert gateway.device_category is None
    assert gateway.wifi_strength == 44
    assert gateway.locked is True
    assert gateway.locking is False
    assert gateway.secure is True
    assert gateway.modules == ["velux_opener_awning", "velux_opener_blind"]

    opener = home.modules["velux_opener_awning"]
    assert opener.device_type == DeviceType.NXO
    assert opener.device_category == DeviceCategory.shutter
    assert opener.name == "Bedroom Awning"
    assert opener.bridge == "velux_gateway_id"
    assert opener.current_position == 100
    assert opener.target_position == 100
    assert opener.mode == "algo_disabled"
    assert opener.reachable is True
    assert opener.silent is False
    assert opener.velux_type == "awning_blind"
    assert opener.manufacturer == "Netatmo"
    assert opener.firmware_revision == 14

    blind = home.modules["velux_opener_blind"]
    assert blind.name == "Bedroom Blind"

    room = home.rooms["velux_room_id"]
    assert room.device_types == {DeviceType.NXO}


async def test_async_shutter_nxo(async_auth):
    """Test VELUX cover control payloads."""
    homesdata = json.loads(load_fixture("homesdata_velux.json"))
    homestatus = json.loads(load_fixture("homestatus_velux_home_id.json"))

    account = pyatmo.AsyncAccount(async_auth)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(
            side_effect=[
                MockResponse(homesdata, 200),
                MockResponse(homestatus, 200),
            ],
        ),
    ):
        await account.async_update_topology()
        await account.async_update_status("velux_home_id")

    module = account.homes["velux_home_id"].modules["velux_opener_awning"]

    def gen_json_data(position):
        return {
            "json": {
                "home": {
                    "id": "velux_home_id",
                    "modules": [
                        {
                            "bridge": "velux_gateway_id",
                            "id": "velux_opener_awning",
                            "target_position": position,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse({"status": "ok"}, 200)),
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
