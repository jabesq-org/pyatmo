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
    assert gateway.modules == [
        "velux_opener_awning",
        "velux_opener_blind",
        "velux_climate_sensor",
        "velux_departure_switch",
    ]

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

    sensor = home.modules["velux_climate_sensor"]
    assert isinstance(sensor, pyatmo.modules.NXS)
    assert {
        "device_type": sensor.device_type,
        "device_category": sensor.device_category,
        "name": sensor.name,
        "bridge": sensor.bridge,
        "room_id": sensor.room_id,
        "setup_date": sensor.setup_date,
        "reachable": sensor.reachable,
        "battery_level": sensor.battery_level,
        "battery_percent": sensor.battery_percent,
        "battery_state": sensor.battery_state,
        "rf_state": sensor.rf_state,
        "rf_strength": sensor.rf_strength,
        "firmware_revision": sensor.firmware_revision,
        "last_seen": sensor.last_seen,
    } == {
        "device_type": DeviceType.NXS,
        "device_category": DeviceCategory.sensor,
        "name": "Bedroom Indoor Climate Sensor",
        "bridge": "velux_gateway_id",
        "room_id": "velux_room_id",
        "setup_date": 1543250432,
        "reachable": True,
        "battery_level": 3724,
        "battery_percent": 38,
        "battery_state": "medium",
        "rf_state": "high",
        "rf_strength": 64,
        "firmware_revision": 16,
        "last_seen": 1776675797,
    }

    departure_switch = home.modules["velux_departure_switch"]
    assert isinstance(departure_switch, pyatmo.modules.NXD)
    assert {
        "device_type": departure_switch.device_type,
        "device_category": departure_switch.device_category,
        "name": departure_switch.name,
        "bridge": departure_switch.bridge,
        "room_id": departure_switch.room_id,
        "setup_date": departure_switch.setup_date,
        "reachable": departure_switch.reachable,
        "battery_level": departure_switch.battery_level,
        "battery_percent": departure_switch.battery_percent,
        "battery_state": departure_switch.battery_state,
        "rf_state": departure_switch.rf_state,
        "rf_strength": departure_switch.rf_strength,
        "firmware_revision": departure_switch.firmware_revision,
        "last_seen": departure_switch.last_seen,
    } == {
        "device_type": DeviceType.NXD,
        "device_category": None,
        "name": "Departure Switch",
        "bridge": "velux_gateway_id",
        "room_id": None,
        "setup_date": 1542892682,
        "reachable": True,
        "battery_level": 2332,
        "battery_percent": 18,
        "battery_state": "low",
        "rf_state": "low",
        "rf_strength": 76,
        "firmware_revision": 16,
        "last_seen": 1776675797,
    }

    room = home.rooms["velux_room_id"]
    assert room.device_types == {DeviceType.NXO, DeviceType.NXS}
    assert {
        "temperature": room.temperature,
        "co2": room.co2,
        "humidity": room.humidity,
        "lux": room.lux,
        "air_quality": room.air_quality,
        "algo_status": room.algo_status,
        "algo_schedule_start": room.algo_schedule_start,
        "auto_close_ts": room.auto_close_ts,
        "min_comfort_temperature": room.min_comfort_temperature,
        "max_comfort_temperature": room.max_comfort_temperature,
        "min_comfort_humidity": room.min_comfort_humidity,
        "max_comfort_humidity": room.max_comfort_humidity,
        "max_comfort_co2": room.max_comfort_co2,
    } == {
        "temperature": 249,
        "co2": 812,
        "humidity": 56,
        "lux": 6,
        "air_quality": 1,
        "algo_status": 1,
        "algo_schedule_start": 600,
        "auto_close_ts": 0,
        "min_comfort_temperature": 180,
        "max_comfort_temperature": 230,
        "min_comfort_humidity": 20,
        "max_comfort_humidity": 70,
        "max_comfort_co2": 1150,
    }


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
