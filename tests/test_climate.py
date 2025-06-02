"""Define tests for climate module."""

import json
from unittest.mock import AsyncMock, patch

import anyio
import pytest

from pyatmo import DeviceType, NoScheduleError
from pyatmo.modules import NATherm1
from pyatmo.modules.device_types import DeviceCategory
from tests.common import MockResponse, fake_post_request
from tests.conftest import does_not_raise


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


async def test_async_climate_NATherm1(async_home):
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


async def test_async_climate_NRV(async_home):
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


async def test_async_climate_NAPlug(async_home):
    """Test NAPlug climate device."""
    module_id = "12:34:56:00:fa:d0"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NAPlug
    assert len(module.modules) == 3
    assert module.rf_strength == 107
    assert module.wifi_strength == 42
    assert module.firmware_revision == 174


async def test_async_climate_NIS(async_home):
    """Test Netatmo siren."""
    module_id = "12:34:56:00:e3:9b"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NIS
    assert module.firmware_revision == 209
    assert module.status == "no_sound"
    assert module.monitoring is False


async def test_async_climate_OTM(async_home):
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


async def test_async_climate_OTH(async_home):
    """Test OTH climate device."""
    module_id = "12:34:56:20:f5:44"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.OTH
    assert len(module.modules) == 1
    assert module.wifi_strength == 57
    assert module.firmware_revision == 22


async def test_async_climate_BNS(async_home):
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


async def test_async_climate_initial_state(async_account):
    """Test initial climate state."""
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


async def test_async_climate_disconnected_state(async_account):
    """Test climate state when disconnected."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    home = async_account.homes[home_id]
    room_id = "2746182631"
    room = home.rooms[room_id]
    module_id = "12:34:56:00:01:ae"
    module = home.modules[module_id]

    async with await anyio.open_file(
        "fixtures/home_status_error_disconnected.json",
        encoding="utf-8",
    ) as json_file:
        content = await json_file.read()
        home_status_fixture = json.loads(content)
    mock_home_status_resp = MockResponse(home_status_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_home_status_resp),
    ) as mock_request:
        await async_account.async_update_status(home_id)
        mock_request.assert_called()

    assert room.reachable is None
    assert module.reachable is False


async def test_async_climate_reconnected_state(async_account):
    """Test climate state after reconnection."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    home = async_account.homes[home_id]
    room_id = "2746182631"
    room = home.rooms[room_id]
    module_id = "12:34:56:00:01:ae"
    module = home.modules[module_id]

    async with await anyio.open_file(
        "fixtures/home_status_simple.json",
        encoding="utf-8",
    ) as json_file:
        home_status_fixture = json.loads(await json_file.read())
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
    ("t_sched_id", "expected"),
    [
        ("591b54a2764ff4d50d8b5795", does_not_raise()),
        (
            "123456789abcdefg12345678",
            pytest.raises(NoScheduleError),
        ),
    ],
)
async def test_async_climate_switch_schedule(
    async_home,
    t_sched_id,
    expected,
):
    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            AsyncMock(return_value=MockResponse(response, 200)),
        ),
        expected,
    ):
        await async_home.async_switch_schedule(
            schedule_id=t_sched_id,
        )


@pytest.mark.parametrize(
    ("temp", "end_time"),
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

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

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
    ("mode", "end_time", "schedule_id", "json_fixture", "expected", "exception"),
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
            pytest.raises(NoScheduleError),
        ),
        (
            "away",
            1559162650,
            0000000,
            "status_ok.json",
            True,
            pytest.raises(NoScheduleError),
        ),
        (
            "schedule",
            None,
            "blahblahblah",
            "home_status_error_invalid_schedule_id.json",
            False,
            pytest.raises(NoScheduleError),
        ),
    ],
)
async def test_async_climate_set_thermmode(
    async_home,
    mode,
    end_time,
    schedule_id,
    json_fixture,
    expected,
    exception,
):
    async with await anyio.open_file(
        f"fixtures/{json_fixture}",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            AsyncMock(return_value=MockResponse(response, 200)),
        ),
        exception,
    ):
        resp = await async_home.async_set_thermmode(
            mode=mode,
            end_time=end_time,
            schedule_id=schedule_id,
        )
        assert expected is resp


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


async def test_power_wire(async_home_multi):
    """Test room with climate devices."""
    room_id = "3707962039"
    assert room_id in async_home_multi.rooms

    room = async_home_multi.rooms[room_id]

    assert room.climate_type == DeviceType.NLC
    assert DeviceType.NLC in room.device_types
    assert room.support_pilot_wire is True
