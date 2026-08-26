"""Define shared fixtures."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo

from .common import (
    fake_post_request,
    fake_post_request_ac,
    fake_post_request_bridged,
    fake_post_request_bticino,
    fake_post_request_multi,
)


@contextmanager
def does_not_raise():
    yield


@pytest.fixture
async def async_auth():
    """AsyncAuth fixture."""
    with patch("pyatmo.auth.AbstractAsyncAuth", AsyncMock()) as auth:
        yield auth


@pytest.fixture
async def async_account(async_auth):
    """AsyncAccount fixture."""
    account: pyatmo.AsyncAccount = pyatmo.AsyncAccount(async_auth)

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            fake_post_request,
        ),
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_request",
            fake_post_request,
        ),
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture
async def async_home(async_account):
    """AsyncClimate fixture for home_id 91763b24c43d3e344f424e8b."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    return async_account.homes[home_id]


@pytest.fixture
async def async_account_multi(async_auth):
    """AsyncAccount fixture."""
    account: pyatmo.AsyncAccount = pyatmo.AsyncAccount(
        async_auth,
        disabled_homes_ids=["eeeeeeeeeffffffffffaaaaa"],
    )

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            fake_post_request_multi,
        ),
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_request",
            fake_post_request_multi,
        ),
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture
async def async_home_multi(async_account_multi):
    """AsyncClimate fixture for home_id 91763b24c43d3e344f424e8b."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"
    return async_account_multi.homes[home_id]


@pytest.fixture
async def async_account_ac(async_auth):
    """AsyncAccount fixture for the capture-derived AC home.

    Unlike `homesdata.json`, this home's /homesdata carries no `reachable` key on
    any module, which is what the real API does. Use it for anything that depends
    on reachability resolution.
    """
    account: pyatmo.AsyncAccount = pyatmo.AsyncAccount(async_auth)

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            fake_post_request_ac,
        ),
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_request",
            fake_post_request_ac,
        ),
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture
async def async_home_ac(async_account_ac):
    """Home fixture for the capture-derived AC home, after a /homestatus update."""
    home_id = "ac_home_id"
    await async_account_ac.async_update_status(home_id)
    return async_account_ac.homes[home_id]


@pytest.fixture
async def async_account_bridged(async_auth):
    """AsyncAccount fixture for a second capture-derived home.

    A different account from the AC home, with the same shape: bridges that never
    report `reachable` and rooms missing from /homestatus. Use it to check that the
    cascade behaviour is a property of the API, not of one capture.
    """
    account: pyatmo.AsyncAccount = pyatmo.AsyncAccount(async_auth)

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            fake_post_request_bridged,
        ),
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_request",
            fake_post_request_bridged,
        ),
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture
async def async_home_bridged(async_account_bridged):
    """Home fixture for the second capture-derived home, after /homestatus."""
    home_id = "bridged_home_id"
    await async_account_bridged.async_update_status(home_id)
    return async_account_bridged.homes[home_id]


@pytest.fixture
async def async_account_bticino(async_auth):
    """AsyncAccount fixture for a BTicino MyHome Server 1 (MHS1) home."""
    account: pyatmo.AsyncAccount = pyatmo.AsyncAccount(async_auth)

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            fake_post_request_bticino,
        ),
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_request",
            fake_post_request_bticino,
        ),
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture
async def async_home_bticino(async_account_bticino):
    """Home fixture for the BTicino MHS1 home, after a /homestatus update."""
    home_id = "bticino_home_id"
    await async_account_bticino.async_update_status(home_id)
    return async_account_bticino.homes[home_id]
