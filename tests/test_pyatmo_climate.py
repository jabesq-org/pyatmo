"""Define tests for climate module."""
import pytest

# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_climate(async_climate):
    """Test basic climate setup."""
    home_id = "91763b24c43d3e344f424e8b"
    assert home_id in async_climate.homes

    home = async_climate.homes[home_id]

    room_id = "2746182631"
    assert room_id in home.rooms

    room = home.rooms[room_id]

    module_id = "12:34:56:00:01:ae"
    assert module_id in room.modules
    assert module_id in home.modules
    assert home.modules[module_id].name == "Livingroom"

    schedule_id = "591b54a2764ff4d50d8b5795"
    selected_schedule = home.get_selected_schedule()
    assert selected_schedule.entity_id == schedule_id
    assert home.is_valid_schedule(schedule_id)
    assert not home.is_valid_schedule("123")
    assert home.get_hg_temp() == 7
    assert home.get_away_temp() == 14


@pytest.mark.asyncio
async def test_async_climate_empty_home(async_climate):
    """Test empty home."""
    home_id = "91763b24c43d3e344f424e8c"

    assert home_id in async_climate.homes

    home = async_climate.homes[home_id]

    assert home.rooms == {}
