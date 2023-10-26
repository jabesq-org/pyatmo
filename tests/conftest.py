"""Define shared fixtures."""
# pylint: disable=redefined-outer-name, protected-access
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pyatmo
import pytest

from .common import fake_post_request


@contextmanager
def does_not_raise():
    yield


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
