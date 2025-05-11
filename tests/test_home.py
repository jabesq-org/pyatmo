"""Define tests for home module."""

import json
from unittest.mock import AsyncMock, patch

import anyio
import pytest

import pyatmo
from pyatmo import DeviceType, NoDeviceError
from tests.common import MockResponse


async def test_async_home(async_home):
    """Test basic home setup."""
    room_id = "3688132631"
    room = async_home.rooms[room_id]
    assert room.device_types == {
        DeviceType.NDB,
        DeviceType.NACamera,
        DeviceType.NBR,
        DeviceType.NIS,
        DeviceType.NBO,
        DeviceType.NPC,
        DeviceType.NLPD,
    }
    assert len(async_home.rooms) == 9
    assert len(async_home.modules) == 51
    assert async_home.modules != room.modules

    module_id = "12:34:56:10:f1:66"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NDB

    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC

    assert async_home.temperature_control_mode == "cooling"


async def test_async_home_set_schedule(async_home):
    """Test home schedule."""
    schedule_id = "591b54a2764ff4d50d8b5795"
    selected_schedule = async_home.get_selected_schedule()
    assert selected_schedule.entity_id == schedule_id
    assert async_home.is_valid_schedule(schedule_id)
    assert not async_home.is_valid_schedule("123")
    assert async_home.get_hg_temp() == 7
    assert async_home.get_away_temp() == 14


async def test_async_home_data_no_body(async_auth):
    """Test home data with no body."""
    async with await anyio.open_file(
        "fixtures/homesdata_empty.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.loads(await fixture_file.read())

    mock_request = AsyncMock(return_value=MockResponse(json_fixture, 200))
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        mock_request,
    ):
        climate = pyatmo.AsyncAccount(async_auth)
        with pytest.raises(NoDeviceError):
            await climate.async_update_topology()
        mock_request.assert_awaited_once()


async def test_async_set_persons_home(async_account):
    """Test marking a person being at home."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]

    person_ids = [
        "91827374-7e04-5298-83ad-a0cb8372dff1",
        "91827375-7e04-5298-83ae-a0cb8372dff2",
    ]

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        await home.async_set_persons_home(person_ids)

        mock_resp.assert_awaited_with(
            params={"home_id": home_id, "person_ids[]": person_ids},
            endpoint="api/setpersonshome",
        )


async def test_async_set_persons_away(async_account):
    """Test marking a set of persons being away."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

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


def test_device_types_missing():
    """Test handling of missing device types."""

    assert DeviceType("NOC") == DeviceType.NOC
    assert DeviceType("UNKNOWN") == DeviceType.NLunknown
