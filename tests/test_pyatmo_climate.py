"""Define tests for climate module."""
import json
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo

from tests.conftest import MockResponse, does_not_raise

# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_climate(async_auth, async_climate):
    """Test basic climate setup."""
    home_id = "91763b24c43d3e344f424e8b"
    assert home_id in async_climate.homes

    home = async_climate.homes[home_id]

    room_id = "2746182631"
    assert room_id in home.rooms
    assert len(home.rooms) == 4

    room = home.rooms[room_id]
    assert room.reachable is True

    module_id = "12:34:56:00:01:ae"
    assert module_id in home.modules
    assert len(home.modules) == 5
    assert module_id in room.modules
    assert home.modules != room.modules
    assert len(room.modules) == 1

    module = home.modules[module_id]
    assert module.name == "Livingroom"
    assert module.device_type == pyatmo.climate.NetatmoDeviceType.NATherm1
    assert module.reachable is True

    module_id = "12:34:56:03:a5:54"
    module = home.modules[module_id]
    assert module.name == "Valve1"
    assert home.rooms[module.room_id].name == "Entrada"
    assert module.device_type == pyatmo.climate.NetatmoDeviceType.NRV
    assert module.reachable is True

    schedule_id = "591b54a2764ff4d50d8b5795"
    selected_schedule = home.get_selected_schedule()
    assert selected_schedule.entity_id == schedule_id
    assert home.is_valid_schedule(schedule_id)
    assert not home.is_valid_schedule("123")
    assert home.get_hg_temp() == 7
    assert home.get_away_temp() == 14

    relay_id = "12:34:56:00:fa:d0"
    assert relay_id in home.modules
    relay = home.modules[relay_id]
    assert relay.device_type == pyatmo.climate.NetatmoDeviceType.NAPlug
    assert len(relay.modules) == 3


@pytest.mark.asyncio
async def test_async_climate_update(async_climate):
    """Test basic climate state update."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_climate.homes[home_id]

    room_id = "2746182631"
    room = home.rooms[room_id]

    module_id = "12:34:56:00:01:ae"
    module = home.modules[module_id]
    assert room.reachable is True
    assert module.name == "Livingroom"
    assert module.device_type == pyatmo.climate.NetatmoDeviceType.NATherm1
    assert module.reachable is True

    with open(
        "fixtures/home_status_error_disconnected.json",
        encoding="utf-8",
    ) as json_file:
        home_status_fixture = json.load(json_file)
    mock_home_status_resp = MockResponse(home_status_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_home_status_resp),
    ) as mock_request:
        await async_climate.async_update()
        mock_request.assert_called()

    assert room.reachable is False
    assert module.reachable is False

    with open("fixtures/home_status_simple.json", encoding="utf-8") as json_file:
        home_status_fixture = json.load(json_file)
    mock_home_status_resp = MockResponse(home_status_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_home_status_resp),
    ) as mock_request:
        await async_climate.async_update()
        mock_request.assert_called()

    assert room.reachable is True
    assert module.reachable is True


@pytest.mark.parametrize(
    "t_sched_id, expected",
    [
        ("591b54a2764ff4d50d8b5795", does_not_raise()),
        (
            "123456789abcdefg12345678",
            pytest.raises(pyatmo.NoSchedule),
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_climate_switch_home_schedule(
    async_climate,
    t_sched_id,
    expected,
):
    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ):
        with expected:
            await async_climate.async_switch_home_schedule(
                schedule_id=t_sched_id,
            )


@pytest.mark.parametrize(
    "mode, end_time, schedule_id, json_fixture, expected, exception",
    [
        (
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
            pytest.raises(pyatmo.NoSchedule),
        ),
        (
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
            pytest.raises(pyatmo.NoSchedule),
        ),
        (
            "away",
            None,
            None,
            "status_ok.json",
            "ok",
            does_not_raise(),
        ),
        (
            "away",
            1559162650,
            None,
            "status_ok.json",
            "ok",
            does_not_raise(),
        ),
        (
            "away",
            1559162650,
            0000000,
            "status_ok.json",
            "ok",
            pytest.raises(pyatmo.NoSchedule),
        ),
        (
            "schedule",
            None,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            "ok",
            does_not_raise(),
        ),
        (
            "schedule",
            1559162650,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            "ok",
            does_not_raise(),
        ),
        (
            "schedule",
            None,
            "blahblahblah",
            "home_status_error_invalid_schedule_id.json",
            "schedule <blahblahblah> is not therm schedule",
            pytest.raises(pyatmo.NoSchedule),
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_climate_set_thermmode(
    async_climate,
    mode,
    end_time,
    schedule_id,
    json_fixture,
    expected,
    exception,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ), exception:
        res = await async_climate.async_set_thermmode(
            mode=mode,
            end_time=end_time,
            schedule_id=schedule_id,
        )
        if "error" in res:
            assert expected in res["error"]["message"]
        else:
            assert expected in res["status"]


@pytest.mark.parametrize(
    "room_id, mode, temp, end_time, json_fixture, expected",
    [
        (
            "2746182631",
            "home",
            14,
            None,
            "status_ok.json",
            "ok",
        ),
        (
            "2746182631",
            "home",
            14,
            1559162650,
            "status_ok.json",
            "ok",
        ),
        (
            "2746182631",
            "home",
            None,
            None,
            "status_ok.json",
            "ok",
        ),
        (
            "2746182631",
            "home",
            None,
            1559162650,
            "status_ok.json",
            "ok",
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_climate_set_room_thermpoint(
    async_climate,
    room_id,
    mode,
    temp,
    end_time,
    json_fixture,
    expected,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ):
        result = await async_climate.async_set_room_thermpoint(
            room_id=room_id,
            mode=mode,
            temp=temp,
            end_time=end_time,
        )
        assert result["status"] == expected
