"""Define tests for climate module."""
import datetime as dt
import json
from unittest.mock import AsyncMock, patch

import pytest
import time_machine

import pyatmo
from pyatmo import DeviceType, NoDevice, NoSchedule
from pyatmo.modules import NATherm1
from pyatmo.modules.base_class import Location, Place
from pyatmo.modules.device_types import DeviceCategory
from tests.common import fake_post_request
from tests.conftest import MockResponse, does_not_raise

# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_home(async_home):
    """Test basic home setup."""
    room_id = "3688132631"
    room = async_home.rooms[room_id]
    assert room.device_types == {
        DeviceType.NDB,
        DeviceType.NACamera,
        DeviceType.NBR,
        DeviceType.NIS,
    }
    assert len(async_home.rooms) == 8
    assert len(async_home.modules) == 35
    assert async_home.modules != room.modules

    module_id = "12:34:56:10:f1:66"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NDB

    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC


@pytest.mark.asyncio
async def test_async_climate_room(async_home):
    """Test room with climate devices."""
    room_id = "2746182631"
    assert room_id in async_home.rooms

    room = async_home.rooms[room_id]
    assert room.reachable is True
    assert room.device_types == {DeviceType.NATherm1}

    module_id = "12:34:56:00:01:ae"
    assert module_id in room.modules
    assert len(room.modules) == 1


@pytest.mark.asyncio
async def test_async_climate_NATherm1(async_home):  # pylint: disable=invalid-name
    """Test NATherm1 climate device."""
    module_id = "12:34:56:00:01:ae"
    module = async_home.modules[module_id]
    assert module.name == "Livingroom"
    assert module.device_type == DeviceType.NATherm1
    assert module.reachable is True
    assert module.boiler_status is False
    assert module.firmware_revision == 65
    assert module.battery == 75
    assert module.rf_strength == 58


@pytest.mark.asyncio
async def test_async_climate_NRV(async_home):  # pylint: disable=invalid-name
    """Test NRV climate device."""
    module_id = "12:34:56:03:a5:54"
    module = async_home.modules[module_id]
    assert module.name == "Valve1"
    assert async_home.rooms[module.room_id].name == "Entrada"
    assert module.device_type == DeviceType.NRV
    assert module.reachable is True
    assert module.rf_strength == 51
    assert module.battery == 90
    assert module.firmware_revision == 79


@pytest.mark.asyncio
async def test_async_climate_NAPlug(async_home):  # pylint: disable=invalid-name
    """Test NAPlug climate device."""
    module_id = "12:34:56:00:fa:d0"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NAPlug
    assert len(module.modules) == 3
    assert module.rf_strength == 107
    assert module.wifi_strength == 42
    assert module.firmware_revision == 174


@pytest.mark.asyncio
async def test_async_climate_NIS(async_home):  # pylint: disable=invalid-name
    """Test Netatmo siren."""
    module_id = "12:34:56:00:e3:9b"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NIS
    assert module.firmware_revision == 209
    assert module.status == "no_sound"
    assert module.monitoring is False


@pytest.mark.asyncio
async def test_async_climate_OTM(async_home):  # pylint: disable=invalid-name
    """Test OTM climate device."""
    module_id = "12:34:56:20:f5:8c"
    module = async_home.modules[module_id]
    assert module.name == "Bureau Modulate"
    assert module.device_type == DeviceType.OTM
    assert module.reachable is True
    assert module.boiler_status is False
    assert module.firmware_revision == 6
    assert module.battery == 90
    assert module.rf_strength == 64


@pytest.mark.asyncio
async def test_async_climate_OTH(async_home):  # pylint: disable=invalid-name
    """Test OTH climate device."""
    module_id = "12:34:56:20:f5:44"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.OTH
    assert len(module.modules) == 1
    assert module.wifi_strength == 57
    assert module.firmware_revision == 22


@pytest.mark.asyncio
async def test_async_switch_NLP(async_home):  # pylint: disable=invalid-name
    """Test NLP Legrand plug."""
    module_id = "12:34:56:80:00:12:ac:f2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLP
    assert module.firmware_revision == 62
    assert module.on
    assert module.power == 0


@pytest.mark.asyncio
async def test_async_switch_NLF(async_home):  # pylint: disable=invalid-name
    """Test NLF Legrand dimmer."""
    module_id = "00:11:22:33:00:11:45:fe"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLF
    assert module.firmware_revision == 57
    assert module.on is False
    assert module.brightness == 63
    assert module.power == 0


@pytest.mark.asyncio
async def test_async_shutter_NBR(async_home):  # pylint: disable=invalid-name
    """Test NLP Bubendorf iDiamant roller shutter."""
    module_id = "0009999992"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NBR
    assert module.firmware_revision == 16
    assert module.current_position == 0


@pytest.mark.asyncio
async def test_async_weather_NAMain(async_home):  # pylint: disable=invalid-name
    """Test Netatmo weather station main module."""
    module_id = "12:34:56:80:bb:26"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NAMain


@pytest.mark.asyncio
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
    assert module.home.persons[person_id].pseudo == "John Doe"


@pytest.mark.asyncio
async def test_async_energy_NLPC(async_home):  # pylint: disable=invalid-name
    """Test Legrand / BTicino connected energy meter module."""
    module_id = "12:34:56:00:00:a1:4c:da"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLPC
    assert module.power == 476


@pytest.mark.asyncio
async def test_async_climate_BNS(async_home):  # pylint: disable=invalid-name
    """Test Smarther BNS climate module."""
    module_id = "10:20:30:bd:b8:1e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.BNS
    assert module.name == "Smarther"

    room = async_home.rooms[module.room_id]
    assert room.name == "Corridor"
    assert room.device_types == {
        DeviceType.BNS,
    }
    assert room.features == {"humidity", DeviceCategory.climate}


@pytest.mark.asyncio
async def test_async_home_set_schedule(async_home):
    """Test home schedule."""
    schedule_id = "591b54a2764ff4d50d8b5795"
    selected_schedule = async_home.get_selected_schedule()
    assert selected_schedule.entity_id == schedule_id
    assert async_home.is_valid_schedule(schedule_id)
    assert not async_home.is_valid_schedule("123")
    assert async_home.get_hg_temp() == 7
    assert async_home.get_away_temp() == 14


@pytest.mark.asyncio
async def test_async_climate_update(async_account):
    """Test basic climate state update."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    home = async_account.homes[home_id]

    room_id = "2746182631"
    room = home.rooms[room_id]

    module_id = "12:34:56:00:01:ae"
    module = home.modules[module_id]
    assert room.reachable is True
    assert room.humidity is None
    assert module.name == "Livingroom"
    assert module.device_type == DeviceType.NATherm1
    assert module.reachable is True
    assert module.boiler_status is False
    assert module.battery == 75

    assert isinstance(module, NATherm1)

    with open(
        "fixtures/home_status_error_disconnected.json",
        encoding="utf-8",
    ) as json_file:
        home_status_fixture = json.load(json_file)
    mock_home_status_resp = MockResponse(home_status_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_home_status_resp),
    ) as mock_request:
        await async_account.async_update_status(home_id)
        mock_request.assert_called()

    assert room.reachable is None
    assert module.reachable is False

    with open("fixtures/home_status_simple.json", encoding="utf-8") as json_file:
        home_status_fixture = json.load(json_file)
    mock_home_status_resp = MockResponse(home_status_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_home_status_resp),
    ) as mock_request:
        await async_account.async_update_status(home_id)
        mock_request.assert_called()

    assert room.reachable is True
    assert module.reachable is True
    assert module.battery == 75
    assert module.rf_strength == 58


@pytest.mark.parametrize(
    "t_sched_id, expected",
    [
        ("591b54a2764ff4d50d8b5795", does_not_raise()),
        (
            "123456789abcdefg12345678",
            pytest.raises(NoSchedule),
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_climate_switch_schedule(
    async_home,
    t_sched_id,
    expected,
):
    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ):
        with expected:
            await async_home.async_switch_schedule(
                schedule_id=t_sched_id,
            )


@pytest.mark.asyncio
async def test_async_home_data_no_body(async_auth):
    with open("fixtures/homesdata_emtpy_home.json", encoding="utf-8") as fixture_file:
        json_fixture = json.load(fixture_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=json_fixture),
    ) as mock_request:
        climate = pyatmo.AsyncAccount(async_auth)

    with pytest.raises(NoDevice):
        await climate.async_update_topology()
        mock_request.assert_called()


@pytest.mark.parametrize(
    "temp, end_time",
    [
        (
            14,
            None,
        ),
        (
            14,
            1559162650,
        ),
        (
            None,
            None,
        ),
        (
            None,
            1559162650,
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_climate_room_therm_set(
    async_home,
    temp,
    end_time,
):
    room_id = "2746182631"
    mode = "home"

    expected_params = {
        "home_id": "91763b24c43d3e344f424e8b",
        "room_id": room_id,
        "mode": mode,
    }
    if temp:
        expected_params["temp"] = str(temp)
    if end_time:
        expected_params["endtime"] = str(end_time)

    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_post:
        room = async_home.rooms[room_id]

        await room.async_therm_set(
            mode=mode,
            temp=temp,
            end_time=end_time,
        )
        mock_post.assert_awaited_once_with(
            endpoint="api/setroomthermpoint",
            params=expected_params,
        )


@pytest.mark.parametrize(
    "mode, end_time, schedule_id, json_fixture, expected, exception",
    [
        (
            "away",
            None,
            None,
            "status_ok.json",
            True,
            does_not_raise(),
        ),
        (
            "away",
            1559162650,
            None,
            "status_ok.json",
            True,
            does_not_raise(),
        ),
        (
            "schedule",
            None,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            True,
            does_not_raise(),
        ),
        (
            "schedule",
            1559162650,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            True,
            does_not_raise(),
        ),
        (
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            False,
            pytest.raises(NoSchedule),
        ),
        (
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            False,
            pytest.raises(NoSchedule),
        ),
        (
            "away",
            1559162650,
            0000000,
            "status_ok.json",
            True,
            pytest.raises(NoSchedule),
        ),
        (
            "schedule",
            None,
            "blahblahblah",
            "home_status_error_invalid_schedule_id.json",
            False,
            pytest.raises(NoSchedule),
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_climate_set_thermmode(
    async_home,
    mode,
    end_time,
    schedule_id,
    json_fixture,
    expected,
    exception,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        response = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ), exception:
        resp = await async_home.async_set_thermmode(
            mode=mode,
            end_time=end_time,
            schedule_id=schedule_id,
        )
        assert expected is resp


@pytest.mark.asyncio
async def test_async_climate_empty_home(async_account):
    """Test climate setup with empty home."""
    home_id = "91763b24c43d3e344f424e8c"

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_post_request,
    ):
        await async_account.async_update_status(home_id)

    assert home_id in async_account.homes

    home = async_account.homes[home_id]
    assert len(home.rooms) == 0


@pytest.mark.asyncio
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
                            "bridge": "70:ee:50:3e:d5:d4",
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


@pytest.mark.asyncio
async def test_async_NOC(async_home):  # pylint: disable=invalid-name
    """Test basic outdoor camera functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC
    assert module.firmware_revision == 3002000
    assert module.firmware_name == "3.2.0"
    assert module.monitoring is True
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_async_weather_update(async_account):
    """Test basic weather station update."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_weather_stations()
    home = async_account.homes[home_id]

    module_id = "12:34:56:80:bb:26"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NAMain
    assert module.name == "Villa"
    assert module.modules == [
        "12:34:56:80:44:92",
        "12:34:56:80:7e:18",
        "12:34:56:80:1c:42",
        "12:34:56:80:c1:ea",
    ]
    assert module.features == {
        "temperature",
        "humidity",
        "co2",
        "noise",
        "pressure",
        "absolute_pressure",
        "temp_trend",
        "pressure_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "wifi_strength",
        "place",
    }
    assert module.firmware_revision == 181
    assert module.wifi_strength == 57
    assert module.temperature == 21.1
    assert module.humidity == 45
    assert module.co2 == 1339
    assert module.pressure == 1026.8
    assert module.noise == 35
    assert module.absolute_pressure == 974.5
    assert module.place == Place(
        {
            "altitude": 329,
            "city": "Someplace",
            "country": "FR",
            "location": Location(longitude=6.1234567, latitude=46.123456),
            "timezone": "Europe/Paris",
        },
    )

    module_id = "12:34:56:80:44:92"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Bedroom"
    assert module.features == {
        "temperature",
        "temp_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "rf_strength",
        "co2",
        "humidity",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule4
    assert module.modules is None
    assert module.firmware_revision == 51
    assert module.rf_strength == 67
    assert module.temperature == 19.3
    assert module.humidity == 53
    assert module.battery == 28

    module_id = "12:34:56:80:c1:ea"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Rain"
    assert module.features == {
        "sum_rain_1",
        "sum_rain_24",
        "rain",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule3
    assert module.modules is None
    assert module.firmware_revision == 12
    assert module.rf_strength == 79
    assert module.rain == 3.7

    module_id = "12:34:56:80:1c:42"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Outdoor"
    assert module.features == {
        "temperature",
        "humidity",
        "temp_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule1
    assert module.modules is None
    assert module.firmware_revision == 50
    assert module.rf_strength == 68
    assert module.temperature == 9.4
    assert module.humidity == 57

    module_id = "12:34:56:03:1b:e4"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Garden"
    assert module.features == {
        "wind_strength",
        "gust_strength",
        "gust_angle",
        "gust_direction",
        "wind_angle",
        "wind_direction",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule2
    assert module.modules is None
    assert module.firmware_revision == 19
    assert module.rf_strength == 59
    assert module.wind_strength == 4
    assert module.wind_angle == 217
    assert module.gust_strength == 9
    assert module.gust_angle == 206


@pytest.mark.asyncio
async def test_async_weather_favorite(async_account):
    """Test favorite weather station."""
    await async_account.async_update_weather_stations()

    module_id = "00:11:22:2c:be:c8"
    assert module_id in async_account.modules
    module = async_account.modules[module_id]
    assert module.device_type == DeviceType.NAMain
    assert module.name == "Zuhause (Kinderzimmer)"
    assert module.modules == ["00:11:22:2c:ce:b6"]
    assert module.features == {
        "temperature",
        "humidity",
        "co2",
        "noise",
        "pressure",
        "absolute_pressure",
        "temp_trend",
        "pressure_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "wifi_strength",
        "place",
    }
    assert module.pressure == 1015.6
    assert module.absolute_pressure == 1000.4
    assert module.place == Place(
        {
            "altitude": 127,
            "city": "Wiesbaden",
            "country": "DE",
            "location": Location(
                longitude=8.238054275512695,
                latitude=50.07585525512695,
            ),
            "timezone": "Europe/Berlin",
        },
    )

    module_id = "00:11:22:2c:ce:b6"
    assert module_id in async_account.modules
    module = async_account.modules[module_id]
    assert module.device_type == DeviceType.NAModule1
    assert module.name == "Unknown"
    assert module.modules is None
    assert module.features == {
        "temperature",
        "humidity",
        "temp_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.temperature == 7.8
    assert module.humidity == 87


@pytest.mark.asyncio
async def test_async_air_care_update(async_account):
    """Test basic air care update."""
    await async_account.async_update_air_care()

    module_id = "12:34:56:26:68:92"
    assert module_id in async_account.modules
    module = async_account.modules[module_id]

    assert module.device_type == DeviceType.NHC
    assert module.name == "Baby Bedroom"
    assert module.features == {
        "temperature",
        "humidity",
        "co2",
        "noise",
        "pressure",
        "absolute_pressure",
        "temp_trend",
        "pressure_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "health_idx",
        "reachable",
        "wifi_strength",
        "place",
    }

    assert module.modules is None
    assert module.firmware_revision == 45
    assert module.wifi_strength == 68
    assert module.temperature == 21.6
    assert module.humidity == 66
    assert module.co2 == 1053
    assert module.pressure == 1021.4
    assert module.noise == 45
    assert module.absolute_pressure == 1011
    assert module.health_idx == 1


@pytest.mark.asyncio
async def test_async_set_persons_home(async_account):
    """Test marking a person being at home."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]

    person_ids = [
        "91827374-7e04-5298-83ad-a0cb8372dff1",
        "91827375-7e04-5298-83ae-a0cb8372dff2",
    ]

    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        await home.async_set_persons_home(person_ids)

        mock_resp.assert_awaited_with(
            params={"home_id": home_id, "person_ids[]": person_ids},
            endpoint="api/setpersonshome",
        )


@pytest.mark.asyncio
async def test_async_set_persons_away(async_account):
    """Test marking a set of persons being away."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]

    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        response = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        person_id = "91827374-7e04-5298-83ad-a0cb8372dff1"
        await home.async_set_persons_away(person_id)

        mock_resp.assert_awaited_with(
            params={"home_id": home_id, "person_id": person_id},
            endpoint="api/setpersonsaway",
        )

        await home.async_set_persons_away()

        mock_resp.assert_awaited_with(
            params={"home_id": home_id},
            endpoint="api/setpersonsaway",
        )


@pytest.mark.asyncio
async def test_async_public_weather_update(async_account):
    """Test basic public weather update."""
    lon_ne = "6.221652"
    lat_ne = "46.610870"
    lon_sw = "6.217828"
    lat_sw = "46.596485"

    area_id = async_account.register_public_weather_area(lat_ne, lon_ne, lat_sw, lon_sw)
    await async_account.async_update_public_weather(area_id)

    area = async_account.public_weather_areas[area_id]
    assert area.location == pyatmo.modules.netatmo.Location(
        lat_ne,
        lon_ne,
        lat_sw,
        lon_sw,
    )
    assert area.stations_in_area() == 8

    assert area.get_latest_rain() == {
        "70:ee:50:1f:68:9e": 0,
        "70:ee:50:27:25:b0": 0,
        "70:ee:50:36:94:7c": 0.5,
        "70:ee:50:36:a9:fc": 0,
    }

    assert area.get_60_min_rain() == {
        "70:ee:50:1f:68:9e": 0,
        "70:ee:50:27:25:b0": 0,
        "70:ee:50:36:94:7c": 0.2,
        "70:ee:50:36:a9:fc": 0,
    }

    assert area.get_24_h_rain() == {
        "70:ee:50:1f:68:9e": 9.999,
        "70:ee:50:27:25:b0": 11.716000000000001,
        "70:ee:50:36:94:7c": 12.322000000000001,
        "70:ee:50:36:a9:fc": 11.009,
    }

    assert area.get_latest_pressures() == {
        "70:ee:50:1f:68:9e": 1007.3,
        "70:ee:50:27:25:b0": 1012.8,
        "70:ee:50:36:94:7c": 1010.6,
        "70:ee:50:36:a9:fc": 1010,
        "70:ee:50:01:20:fa": 1014.4,
        "70:ee:50:04:ed:7a": 1005.4,
        "70:ee:50:27:9f:2c": 1010.6,
        "70:ee:50:3c:02:78": 1011.7,
    }

    assert area.get_latest_temperatures() == {
        "70:ee:50:1f:68:9e": 21.1,
        "70:ee:50:27:25:b0": 23.2,
        "70:ee:50:36:94:7c": 21.4,
        "70:ee:50:36:a9:fc": 20.1,
        "70:ee:50:01:20:fa": 27.4,
        "70:ee:50:04:ed:7a": 19.8,
        "70:ee:50:27:9f:2c": 25.5,
        "70:ee:50:3c:02:78": 23.3,
    }

    assert area.get_latest_humidities() == {
        "70:ee:50:1f:68:9e": 69,
        "70:ee:50:27:25:b0": 60,
        "70:ee:50:36:94:7c": 62,
        "70:ee:50:36:a9:fc": 67,
        "70:ee:50:01:20:fa": 58,
        "70:ee:50:04:ed:7a": 76,
        "70:ee:50:27:9f:2c": 56,
        "70:ee:50:3c:02:78": 58,
    }

    assert area.get_latest_wind_strengths() == {"70:ee:50:36:a9:fc": 15}

    assert area.get_latest_wind_angles() == {"70:ee:50:36:a9:fc": 17}

    assert area.get_latest_gust_strengths() == {"70:ee:50:36:a9:fc": 31}

    assert area.get_latest_gust_angles() == {"70:ee:50:36:a9:fc": 217}


@pytest.mark.asyncio
async def test_home_event_update(async_account):
    """Test basic event update."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_events(home_id=home_id)
    home = async_account.homes[home_id]

    events = home.events
    assert len(events) == 8

    module_id = "12:34:56:10:b9:0e"
    assert module_id in home.modules
    module = home.modules[module_id]

    events = module.events
    assert len(events) == 5
    assert events[0].event_type == "outdoor"
    assert events[0].video_id == "11111111-2222-3333-4444-b42f0fc4cfad"
    assert events[1].event_type == "connection"


@time_machine.travel(dt.datetime(2022, 2, 12, 7, 59, 49))
@pytest.mark.asyncio
async def test_historical_data_retrieval(async_account):
    """Test retrieval of historical measurements."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_events(home_id=home_id)
    home = async_account.homes[home_id]

    module_id = "12:34:56:00:00:a1:4c:da"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NLPC

    await async_account.async_update_measures(home_id=home_id, module_id=module_id)
    assert module.historical_data[0] == {
        "Wh": 197,
        "duration": 60,
        "startTime": "2022-02-05T08:29:50Z",
        "endTime": "2022-02-05T09:29:49Z",
    }
    assert module.historical_data[-1] == {
        "Wh": 259,
        "duration": 60,
        "startTime": "2022-02-12T07:29:50Z",
        "endTime": "2022-02-12T08:29:49Z",
    }
    assert len(module.historical_data) == 168
