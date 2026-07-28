"""Define tests for the account module."""

import logging
from unittest.mock import patch

import pytest

import pyatmo
from pyatmo import modules

from .common import fake_post_request_multi


async def test_update_devices_unknown_type_falls_back_to_nlunknown(async_account):
    """Test that an unknown standalone device type does not abort the update.

    A getstationsdata/gethomecoachsdata device reporting a ``type`` with no
    matching class in ``pyatmo.modules`` must fall back to ``NLunknown`` instead
    of raising ``AttributeError`` and aborting the whole update.
    """
    device_id = "00:11:22:33:44:55"
    device_data = {
        "_id": device_id,
        "type": "NOSUCHTYPE",
    }

    # Must not raise even though "NOSUCHTYPE" has no matching class.
    await async_account.update_devices({"devices": [device_data]})

    assert device_id in async_account.modules
    assert isinstance(async_account.modules[device_id], modules.NLunknown)


async def test_update_devices_skips_disabled_home(async_auth, caplog):
    """A disabled home is not resurrected via the weather/aircare device path."""
    home_id = "weather_home"
    device_data = {
        "_id": "00:11:22:33:44:55",
        "type": "NAMain",
        "home_id": home_id,
        "home_name": "Weather Home",
        "modules": [],
    }

    # Sanity: without the denylist the same data DOES create the home, and the
    # lazily-created home is registered in the full inventory too.
    enabled = pyatmo.AsyncAccount(async_auth)
    await enabled.update_devices({"devices": [dict(device_data)]})
    assert home_id in enabled.homes
    assert enabled.all_home_names[home_id] == "Weather Home"

    # With the home disabled it must not be added to homes, but it stays in the
    # inventory (like process_topology), and the bulk path stays silent
    # (Netatmo returns all homes every time -- not worth a warning).
    disabled = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=[home_id])
    with caplog.at_level(logging.WARNING):
        await disabled.update_devices({"devices": [dict(device_data)]})
    assert home_id not in disabled.homes
    assert home_id in disabled.all_home_names  # still listed in inventory
    assert "disabled" not in caplog.text


async def test_all_home_names_is_full_inventory(async_account_multi):
    """all_home_names contains every home, including disabled ones."""
    names = async_account_multi.all_home_names
    assert names["aaaaaaaaaaabbbbbbbbbbccc"]  # kept home present
    assert names["eeeeeeeeeffffffffffaaaaa"]  # disabled home still listed


async def test_all_homes_id_deprecated_alias(async_account_multi):
    """all_homes_id returns all_home_names and warns about deprecation."""
    with pytest.warns(DeprecationWarning, match="all_home_names"):
        legacy = async_account_multi.all_homes_id
    assert legacy == async_account_multi.all_home_names


async def test_constructor_stores_disabled_homes_ids(async_auth):
    """Constructor stores the denylist as list state."""
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=["home_x"])
    assert account.disabled_homes_ids == ["home_x"]


async def test_constructor_disabled_homes_ids_defaults_empty(async_auth):
    """No arg means an empty denylist."""
    account = pyatmo.AsyncAccount(async_auth)
    assert account.disabled_homes_ids == []


async def test_set_disabled_homes_updates_state(async_auth):
    """set_disabled_homes replaces the stored denylist; None clears it."""
    account = pyatmo.AsyncAccount(async_auth)
    account.set_disabled_homes(["home_y"])
    assert account.disabled_homes_ids == ["home_y"]
    account.set_disabled_homes(None)
    assert account.disabled_homes_ids == []


async def test_disabled_homes_ids_is_copied(async_auth):
    """The stored denylist is a copy; caller mutation does not leak in."""
    caller_list = ["home_x"]
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=caller_list)
    caller_list.append("home_z")
    assert account.disabled_homes_ids == ["home_x"]  # constructor copied

    setter_list = ["home_a"]
    account.set_disabled_homes(setter_list)
    setter_list.append("home_b")
    assert account.disabled_homes_ids == ["home_a"]  # setter copied


async def test_topology_transition_enable_to_disable(async_auth):
    """A home enabled on first fetch is removed when disabled before a refetch."""
    home_id = "eeeeeeeeeffffffffffaaaaa"
    account = pyatmo.AsyncAccount(async_auth)
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_post_request_multi,
    ):
        await account.async_update_topology()  # unfiltered -> home present
        assert home_id in account.homes

        account.set_disabled_homes([home_id])
        await account.async_update_topology()  # refetch respects new denylist

    assert home_id not in account.homes  # removed from active homes
    assert home_id in account.all_home_names  # still in the inventory


async def test_topology_applies_stored_denylist(async_auth):
    """Topology filtering uses the stored disabled_homes_ids denylist."""
    account = pyatmo.AsyncAccount(
        async_auth, disabled_homes_ids=["eeeeeeeeeffffffffffaaaaa"]
    )
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_post_request_multi,
    ):
        await account.async_update_topology()

    assert "eeeeeeeeeffffffffffaaaaa" not in account.homes
    assert "aaaaaaaaaaabbbbbbbbbbccc" in account.homes
    assert "eeeeeeeeeffffffffffaaaaa" in account.all_home_names


async def test_update_status_disabled_home_skips_call(async_auth, caplog):
    """A disabled home_id logs a warning and makes no API request."""
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=["home_disabled"])

    with caplog.at_level(logging.WARNING):
        result = await account.async_update_status("home_disabled")

    assert result is None
    async_auth.async_post_api_request.assert_not_called()
    assert "home_disabled" in caplog.text


async def test_update_events_disabled_home_skips_call(async_auth, caplog):
    """A disabled home_id logs a warning and makes no API request."""
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=["home_disabled"])

    with caplog.at_level(logging.WARNING):
        await account.async_update_events("home_disabled")

    async_auth.async_post_api_request.assert_not_called()
    assert "home_disabled" in caplog.text


async def test_update_measures_disabled_home_skips_call(async_auth, caplog):
    """A disabled home_id logs a warning and makes no API request."""
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=["home_disabled"])

    with caplog.at_level(logging.WARNING):
        await account.async_update_measures("home_disabled", "module_x")

    async_auth.async_post_api_request.assert_not_called()
    assert "home_disabled" in caplog.text


async def test_set_state_disabled_home_skips_call(async_auth, caplog):
    """A disabled home_id logs a warning and makes no API request."""
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=["home_disabled"])

    with caplog.at_level(logging.WARNING):
        await account.async_set_state("home_disabled", {"foo": "bar"})

    async_auth.async_post_api_request.assert_not_called()
    assert "home_disabled" in caplog.text
