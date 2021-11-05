"""Define tests for climate module."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from .conftest import MockResponse

# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_climate(async_climate):
    """Test basic climate setup."""
    home_id = "91763b24c43d3e344f424e8b"
    assert home_id in async_climate.homes
    assert len(async_climate.homes) == 2

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
    assert module.device_type == "NATherm1"
    assert module.reachable is True

    module_id = "12:34:56:03:a5:54"
    module = home.modules[module_id]
    assert module.name == "Valve1"
    assert home.rooms[module.room_id].name == "Entrada"
    assert module.device_type == "NRV"
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
    assert relay.device_type == "NAPlug"
    assert len(relay.modules) == 3


@pytest.mark.asyncio
async def test_async_climate_empty_home(async_climate):
    """Test empty home."""
    home_id = "91763b24c43d3e344f424e8c"

    assert home_id in async_climate.homes

    home = async_climate.homes[home_id]
    assert home.rooms == {}
    assert home.name == "Unknown"


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
    assert module.device_type == "NATherm1"
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
