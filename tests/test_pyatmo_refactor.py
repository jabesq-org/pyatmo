"""Define tests for climate module."""
import json
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo
from pyatmo import NetatmoDeviceType, NoDevice, NoSchedule
from pyatmo.modules import NATherm1

from tests.common import fake_post_request
from tests.conftest import MockResponse, does_not_raise

# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_home(async_home):
    """Test basic home setup."""
    room_id = "3688132631"
    room = async_home.rooms[room_id]
    assert room.device_types == {
        NetatmoDeviceType.NDB,
        NetatmoDeviceType.NACamera,
        NetatmoDeviceType.NBR,
        NetatmoDeviceType.NIS,
    }
    assert len(async_home.rooms) == 6
    assert len(async_home.modules) == 33
    assert async_home.modules != room.modules

    module_id = "12:34:56:10:f1:66"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NDB

    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NOC


@pytest.mark.asyncio
async def test_async_climate_room(async_home):
    """Test room with climate devices."""
    room_id = "2746182631"
    assert room_id in async_home.rooms

    room = async_home.rooms[room_id]
    assert room.reachable is True
    assert room.device_types == {NetatmoDeviceType.NATherm1}

    module_id = "12:34:56:00:01:ae"
    assert module_id in room.modules
    assert len(room.modules) == 1


@pytest.mark.asyncio
async def test_async_climate_NATherm1(async_home):  # pylint: disable=invalid-name
    """Test NATherm1 climate device."""
    module_id = "12:34:56:00:01:ae"
    module = async_home.modules[module_id]
    assert module.name == "Livingroom"
    assert module.device_type == NetatmoDeviceType.NATherm1
    assert module.reachable is True
    assert module.boiler_status is False
    assert module.firmware_revision == 65
    assert module.battery_level == 3793
    assert module.battery_state == "high"
    assert module.rf_strength == 58


@pytest.mark.asyncio
async def test_async_climate_NRV(async_home):  # pylint: disable=invalid-name
    """Test NRV climate device."""
    module_id = "12:34:56:03:a5:54"
    module = async_home.modules[module_id]
    assert module.name == "Valve1"
    assert async_home.rooms[module.room_id].name == "Entrada"
    assert module.device_type == NetatmoDeviceType.NRV
    assert module.reachable is True
    assert module.rf_strength == 51
    assert module.battery_level == 3025
    assert module.battery_state == "full"
    assert module.firmware_revision == 79


@pytest.mark.asyncio
async def test_async_climate_NAPlug(async_home):  # pylint: disable=invalid-name
    """Test NAPlug climate device."""
    module_id = "12:34:56:00:fa:d0"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NAPlug
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
    assert module.device_type == NetatmoDeviceType.NIS
    assert module.firmware_revision == 209
    assert module.status == "no_sound"
    assert module.monitoring is False


@pytest.mark.asyncio
async def test_async_climate_OTM(async_home):  # pylint: disable=invalid-name
    """Test OTM climate device."""
    module_id = "12:34:56:20:f5:8c"
    module = async_home.modules[module_id]
    assert module.name == "Bureau Modulate"
    assert module.device_type == NetatmoDeviceType.OTM
    assert module.reachable is True
    assert module.boiler_status is False
    assert module.firmware_revision == 6
    assert module.battery_level == 4176
    assert module.battery_state == "full"
    assert module.rf_strength == 64


@pytest.mark.asyncio
async def test_async_climate_OTH(async_home):  # pylint: disable=invalid-name
    """Test OTH climate device."""
    module_id = "12:34:56:20:f5:44"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.OTH
    assert len(module.modules) == 1
    assert module.wifi_strength == 57
    assert module.firmware_revision == 22


@pytest.mark.asyncio
async def test_async_climate_NLP(async_home):  # pylint: disable=invalid-name
    """Test NLP Legrand plug."""
    module_id = "12:34:56:80:00:12:ac:f2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NLP
    assert module.firmware_revision == 62
    assert module.on


@pytest.mark.asyncio
async def test_async_climate_NBR(async_home):  # pylint: disable=invalid-name
    """Test NLP Bubendorf iDiamant roller shutter."""
    module_id = "0009999992"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NBR
    assert module.firmware_revision == 16
    assert module.current_position == 0


@pytest.mark.asyncio
async def test_async_climate_NAMain(async_home):  # pylint: disable=invalid-name
    """Test Netatmo weather station main module."""
    module_id = "12:34:56:80:bb:26"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NAMain


@pytest.mark.asyncio
async def test_async_climate_NACamera(async_home):  # pylint: disable=invalid-name
    """Test Netatmo indoor camera module."""
    module_id = "12:34:56:00:f1:62"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NACamera
    person_id = "91827374-7e04-5298-83ad-a0cb8372dff1"
    assert person_id in module.home.persons
    assert module.home.persons[person_id].pseudo == "John Doe"


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
    assert module.name == "Livingroom"
    assert module.device_type == NetatmoDeviceType.NATherm1
    assert module.reachable is True
    assert module.battery_level == 3793
    assert module.boiler_status is False

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
    assert module.battery_level == 3780
    assert module.boiler_status is True
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
async def test_async_climate_switch_home_schedule(
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
            await async_home.async_switch_home_schedule(
                schedule_id=t_sched_id,
            )


@pytest.mark.asyncio
async def test_async_home_data_no_body(async_auth):
    with open("fixtures/homesdata_emtpy_home.json", encoding="utf-8") as fixture_file:
        json_fixture = json.load(fixture_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
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
async def test_async_climate_room_set_thermpoint(
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
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_post:
        room = async_home.rooms[room_id]

        await room.async_set_thermpoint(
            mode=mode,
            temp=temp,
            end_time=end_time,
        )
        mock_post.assert_awaited_once_with(
            url="https://api.netatmo.com/api/setroomthermpoint",
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
    assert module.device_type == NetatmoDeviceType.NBR

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
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_open()
        mock_resp.assert_awaited_with(
            params=gen_json_data(100),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_close()
        mock_resp.assert_awaited_with(
            params=gen_json_data(0),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_set_target_position(47)
        mock_resp.assert_awaited_with(
            params=gen_json_data(47),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_set_target_position(-10)
        mock_resp.assert_awaited_with(
            params=gen_json_data(0),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_set_target_position(101)
        mock_resp.assert_awaited_with(
            params=gen_json_data(100),
            url="https://api.netatmo.com/api/setstate",
        )


@pytest.mark.asyncio
async def test_async_NOC(async_home):  # pylint: disable=invalid-name
    """Test basic outdoor camera functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NOC
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
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_floodlight_on()
        mock_resp.assert_awaited_with(
            params=gen_json_data("on"),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_floodlight_off()
        mock_resp.assert_awaited_with(
            params=gen_json_data("off"),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_floodlight_auto()
        mock_resp.assert_awaited_with(
            params=gen_json_data("auto"),
            url="https://api.netatmo.com/api/setstate",
        )


@pytest.mark.asyncio
async def test_async_camera_monitoring(async_home):
    """Test basic camera monitoring functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NOC

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
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_monitoring_on()
        mock_resp.assert_awaited_with(
            params=gen_json_data("on"),
            url="https://api.netatmo.com/api/setstate",
        )

        assert await module.async_monitoring_off()
        mock_resp.assert_awaited_with(
            params=gen_json_data("off"),
            url="https://api.netatmo.com/api/setstate",
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
    assert module.device_type == NetatmoDeviceType.NAMain
    assert module.modules == [
        "12:34:56:80:44:92",
        "12:34:56:80:7e:18",
        "12:34:56:80:1c:42",
        "12:34:56:80:c1:ea",
    ]
    assert module.firmware_revision == 181
    assert module.wifi_strength == 57
    assert module.temperature == 21.1
    assert module.humidity == 45
    assert module.co2 == 1339
    assert module.pressure == 1026.8
    assert module.noise == 35
    assert module.absolute_pressure == 974.5

    module_id = "12:34:56:80:44:92"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NAModule4
    assert module.modules is None
    assert module.firmware_revision == 51
    assert module.rf_strength == 67
    assert module.temperature == 19.3

    module_id = "12:34:56:80:c1:ea"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NAModule3
    assert module.modules is None
    assert module.firmware_revision == 12
    assert module.rf_strength == 79
    assert module.rain == 3.7

    module_id = "12:34:56:80:1c:42"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NAModule1
    assert module.modules is None
    assert module.firmware_revision == 50
    assert module.rf_strength == 68
    assert module.temperature == 9.4
    assert module.humidity == 57

    module_id = "12:34:56:03:1b:e4"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NAModule2
    assert module.modules is None
    assert module.firmware_revision == 19
    assert module.rf_strength == 59
    assert module.wind_strength == 4
    assert module.wind_angle == 217
    assert module.gust_strength == 9
    assert module.gust_angle == 206


@pytest.mark.asyncio
async def test_async_air_care_update(async_account):
    """Test basic air care update."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_air_care()
    home = async_account.homes[home_id]

    module_id = "12:34:56:26:68:92"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == NetatmoDeviceType.NHC
    assert module.modules is None
    assert module.firmware_revision == 45
    assert module.wifi_strength == 68
    assert module.temperature == 21.6
    assert module.humidity == 66
    assert module.co2 == 1053
    assert module.pressure == 1021.4
    assert module.noise == 45
    assert module.absolute_pressure == 1011
