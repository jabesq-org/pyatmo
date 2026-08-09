"""Define tests for the Smart AC Control and the auto-setpoint room."""

import json
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo
from pyatmo import DeviceType
from tests.common import MockResponse, load_fixture


@pytest.fixture
async def async_home_ac(async_auth):
    """Home fixture built from the anonymised Netatmo capture."""
    homesdata = json.loads(load_fixture("homesdata_ac.json"))
    homestatus = json.loads(load_fixture("homestatus_ac_home_id.json"))

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
        await account.async_update_status("ac_home_id")

    return account.homes["ac_home_id"]


async def test_ac_home_shape(async_home_ac):
    """Pin the fixture topology so a regenerated fixture fails loudly."""
    assert async_home_ac.name == "AC Test Home"
    assert len(async_home_ac.modules) == 11
    assert len(async_home_ac.rooms) == 6

    air_conditioner = async_home_ac.modules["12:34:56:ac:00:11"]
    assert air_conditioner.device_type == DeviceType.NAC
    assert air_conditioner.room_id == "ac_room_living"

    station = async_home_ac.modules["12:34:56:ac:00:01"]
    assert station.device_type == DeviceType.NAMain
    assert station.room_id == "ac_room_living"
