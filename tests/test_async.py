"""Define tests for untility methods."""
# pylint: disable=protected-access
import json
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo

from tests.conftest import does_not_raise

LON_NE = 6.221652
LAT_NE = 46.610870
LON_SW = 6.217828
LAT_SW = 46.596485


@pytest.mark.asyncio
async def test_foo(async_auth):
    with open("fixtures/camera_home_data.json") as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ) as mock_request:
        camera_data = pyatmo.AsyncCameraData(async_auth)
        await camera_data.async_update()

        mock_request.assert_called()
        assert camera_data.homes is not None


@pytest.mark.asyncio
async def test_async_camera_data(async_camera_home_data):
    assert async_camera_home_data.homes is not None


@pytest.mark.asyncio
async def test_async_home_data_no_body(async_auth):
    with open("fixtures/camera_data_empty.json") as fixture_file:
        json_fixture = json.load(fixture_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ) as mock_request:
        camera_data = pyatmo.AsyncCameraData(async_auth)

    with pytest.raises(pyatmo.NoDevice):
        await camera_data.async_update()
        mock_request.assert_called()


@pytest.mark.asyncio
async def test_async_home_data_no_homes(async_auth):
    with open("fixtures/camera_home_data_no_homes.json") as fixture_file:
        json_fixture = json.load(fixture_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ) as mock_request:
        camera_data = pyatmo.AsyncCameraData(async_auth)

    with pytest.raises(pyatmo.NoDevice):
        await camera_data.async_update()
        mock_request.assert_called()


@pytest.mark.asyncio
async def test_async_home_coach_data(async_home_coach_data):
    assert (
        async_home_coach_data.stations["12:34:56:26:69:0c"]["station_name"] == "Bedroom"
    )


@pytest.mark.asyncio
async def test_async_public_data(async_auth):
    with open("fixtures/public_data_simple.json") as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ) as mock_request:
        public_data = pyatmo.AsyncPublicData(async_auth, LAT_NE, LON_NE, LAT_SW, LON_SW)
        await public_data.async_update()

        mock_request.assert_called()
        assert public_data.status == "ok"

        public_data = pyatmo.AsyncPublicData(
            async_auth,
            LAT_NE,
            LON_NE,
            LAT_SW,
            LON_SW,
            required_data_type="temperature,rain_live",
        )
        await public_data.async_update()
        assert public_data.status == "ok"


@pytest.mark.asyncio
async def test_async_public_data_error(async_auth):
    with open("fixtures/public_data_error_mongo.json") as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ):

        public_data = pyatmo.AsyncPublicData(async_auth, LAT_NE, LON_NE, LAT_SW, LON_SW)

        with pytest.raises(pyatmo.NoDevice):
            await public_data.async_update()


@pytest.mark.asyncio
async def test_async_home_data(async_home_data):
    expected = {
        "12:34:56:00:fa:d0": {
            "id": "12:34:56:00:fa:d0",
            "type": "NAPlug",
            "name": "Thermostat",
            "setup_date": 1494963356,
            "modules_bridged": [
                "12:34:56:00:01:ae",
                "12:34:56:03:a0:ac",
                "12:34:56:03:a5:54",
            ],
        },
        "12:34:56:00:01:ae": {
            "id": "12:34:56:00:01:ae",
            "type": "NATherm1",
            "name": "Livingroom",
            "setup_date": 1494963356,
            "room_id": "2746182631",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:03:a5:54": {
            "id": "12:34:56:03:a5:54",
            "type": "NRV",
            "name": "Valve1",
            "setup_date": 1554549767,
            "room_id": "2833524037",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:03:a0:ac": {
            "id": "12:34:56:03:a0:ac",
            "type": "NRV",
            "name": "Valve2",
            "setup_date": 1554554444,
            "room_id": "2940411577",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:00:f1:62": {
            "id": "12:34:56:00:f1:62",
            "type": "NACamera",
            "name": "Hall",
            "setup_date": 1544828430,
            "room_id": "3688132631",
        },
    }
    assert async_home_data.modules["91763b24c43d3e344f424e8b"] == expected


@pytest.mark.asyncio
async def test_async_home_data_no_data(async_auth):
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value="None"),
    ):
        with pytest.raises(pyatmo.NoDevice):
            home_data = pyatmo.AsyncHomeData(async_auth)
            await home_data.async_update()


@pytest.mark.asyncio
async def test_async_data_no_body(async_auth):
    with open("fixtures/home_data_empty.json") as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ):
        home_data = pyatmo.AsyncHomeData(async_auth)
        with pytest.raises(pyatmo.NoDevice):
            await home_data.async_update()


@pytest.mark.parametrize(
    "t_home_id, t_sched_id, expected",
    [
        ("91763b24c43d3e344f424e8b", "591b54a2764ff4d50d8b5795", does_not_raise()),
        (
            "91763b24c43d3e344f424e8b",
            "123456789abcdefg12345678",
            pytest.raises(pyatmo.NoSchedule),
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_home_data_switch_home_schedule(
    async_home_data,
    t_home_id,
    t_sched_id,
    expected,
):
    with open("fixtures/status_ok.json") as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ):
        with expected:
            await async_home_data.async_switch_home_schedule(
                home_id=t_home_id,
                schedule_id=t_sched_id,
            )


@pytest.mark.parametrize(
    "home_id, room_id, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            {
                "id": "2746182631",
                "reachable": True,
                "therm_measured_temperature": 19.8,
                "therm_setpoint_temperature": 12,
                "therm_setpoint_mode": "away",
                "therm_setpoint_start_time": 1559229567,
                "therm_setpoint_end_time": 0,
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_home_status(async_home_status, room_id, expected):
    assert len(async_home_status.rooms) == 3
    assert async_home_status.rooms[room_id] == expected


@pytest.mark.parametrize(
    "home_id, mode, end_time, schedule_id, json_fixture, expected",
    [
        (
            None,
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
        ),
        (
            "91763b24c43d3e344f424e8b",
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
        ),
        (
            "invalidID",
            "away",
            None,
            None,
            "home_status_error_invalid_id.json",
            "Invalid id",
        ),
        ("91763b24c43d3e344f424e8b", "away", None, None, "status_ok.json", "ok"),
        ("91763b24c43d3e344f424e8b", "away", 1559162650, None, "status_ok.json", "ok"),
        (
            "91763b24c43d3e344f424e8b",
            "away",
            1559162650,
            0000000,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "schedule",
            None,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "schedule",
            1559162650,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "schedule",
            None,
            "blahblahblah",
            "home_status_error_invalid_schedule_id.json",
            "schedule <blahblahblah> is not therm schedule",
        ),
    ],
)
@pytest.mark.asyncio
async def test_async_home_status_set_thermmode(
    async_home_status,
    mode,
    end_time,
    schedule_id,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ):
        res = await async_home_status.async_set_thermmode(
            mode=mode,
            end_time=end_time,
            schedule_id=schedule_id,
        )
        if "error" in res:
            assert expected in res["error"]["message"]
        else:
            assert expected in res["status"]


@pytest.mark.parametrize(
    "home_id, room_id, mode, temp, end_time, json_fixture, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            14,
            None,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            14,
            1559162650,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            None,
            None,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
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
async def test_async_home_status_set_room_thermpoint(
    async_home_status,
    room_id,
    mode,
    temp,
    end_time,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=json_fixture),
    ):
        result = await async_home_status.async_set_room_thermpoint(
            room_id=room_id,
            mode=mode,
            temp=temp,
            end_time=end_time,
        )
        assert result["status"] == expected
