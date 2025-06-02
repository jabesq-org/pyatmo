"""Define shared fixtures."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo

from .common import fake_post_request, fake_post_request_multi


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
    account: pyatmo.AsyncAccount = pyatmo.AsyncAccount(async_auth)

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
        await account.async_update_topology(
            disabled_homes_ids=["eeeeeeeeeffffffffffaaaaa"],
        )
        yield account


@pytest.fixture
async def async_home_multi(async_account_multi):
    """AsyncClimate fixture for home_id 91763b24c43d3e344f424e8b."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"
    return async_account_multi.homes[home_id]
