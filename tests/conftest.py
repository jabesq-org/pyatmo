"""Define shared fixtures."""
# pylint: disable=redefined-outer-name, protected-access
from contextlib import contextmanager
import json
from unittest.mock import AsyncMock, patch

import pyatmo
import pytest

from .common import fake_post_request


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def camera_ping(requests_mock):
    """Camera ping fixture."""
    for index in ["w", "z", "g"]:
        vpn_url = (
            f"https://prodvpn-eu-2.netatmo.net/restricted/10.255.248.91/"
            f"6d278460699e56180d47ab47169efb31/"
            f"MpEylTU2MDYzNjRVD-LJxUnIndumKzLboeAwMDqTT{index},,"
        )
        with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
            json_fixture = json.load(json_file)
        requests_mock.post(
            f"{vpn_url}/command/ping",
            json=json_fixture,
            headers={"content-type": "application/json"},
        )

    local_url = "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        f"{local_url}/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )


@pytest.fixture(scope="function")
async def async_auth():
    """AsyncAuth fixture."""
    with patch("pyatmo.auth.AbstractAsyncAuth", AsyncMock()) as auth:
        yield auth


@pytest.fixture(scope="function")
async def async_account(async_auth):
    """AsyncAccount fixture."""
    account = pyatmo.AsyncAccount(async_auth)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_post_request,
    ), patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        fake_post_request,
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture(scope="function")
async def async_home(async_account):
    """AsyncClimate fixture for home_id 91763b24c43d3e344f424e8b."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    yield async_account.homes[home_id]
