"""Define tests for the Legrand gateway home: NLG, NLY, NSD and NCO."""

import json
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo
from pyatmo import DeviceType
from tests.common import MockResponse, load_fixture


@pytest.fixture
async def async_home_legrand(async_auth):
    """Home fixture built from the anonymised Legrand capture."""
    homesdata = json.loads(load_fixture("homesdata_legrand.json"))
    homestatus = json.loads(load_fixture("homestatus_legrand_home_id.json"))

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
        await account.async_update_status("legrand_home_id")

    return account.homes["legrand_home_id"]


async def test_legrand_home_shape(async_home_legrand):
    """Pin the fixture topology so a regenerated fixture fails loudly."""
    assert async_home_legrand.name == "Legrand Test Home"
    assert len(async_home_legrand.modules) == 11
    assert len(async_home_legrand.rooms) == 2

    gateway = async_home_legrand.modules["12:34:56:aa:00:01"]
    assert gateway.device_type == DeviceType.NLG
    assert gateway.modules == [
        "12:34:56:aa:00:02",
        "12:34:56:aa:00:02#1",
        "12:34:56:aa:00:02#2",
        "12:34:56:aa:00:02#3",
    ]

    meter = async_home_legrand.modules["12:34:56:aa:00:02"]
    assert meter.device_type == DeviceType.NLY
    assert meter.bridge == "12:34:56:aa:00:01"

    assert async_home_legrand.modules["12:34:56:aa:00:03"].device_type == DeviceType.NSD
    assert async_home_legrand.modules["12:34:56:aa:00:04"].device_type == DeviceType.NCO
