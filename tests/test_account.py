"""Define tests for the account module."""

import logging
from unittest.mock import patch

import pytest

import pyatmo
from pyatmo import modules
from pyatmo.const import INVALID_HOME_ERROR_CODE
from pyatmo.exceptions import NoDeviceError

from .common import MockResponse, fake_post_request_multi


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


async def test_update_status_body_less_response_names_the_home(async_account, caplog):
    """A 200 without a `body` names the home the /homestatus call was for.

    The real API answers `{"status": "ok", "time_server": ...}` for some homes,
    and the resulting NoDeviceError used to be unattributable on an account
    holding more than one home.
    """
    home_id = "91763b24c43d3e344f424e8b"

    async def _body_less_response(*_args, **_kwargs):
        return MockResponse({"status": "ok", "time_server": 1786656837}, 200)

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            _body_less_response,
        ),
        caplog.at_level(logging.DEBUG, logger="pyatmo.helpers"),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        await async_account.async_update_status(home_id)

    assert f"for home {home_id}" in str(exc_info.value)
    assert f"for home {home_id}" in caplog.text


async def test_update_status_rejected_home_raises_invalid_home_error(async_account):
    """A home the API rejects with 400 + code 21 surfaces as InvalidHomeError.

    The translation lives here rather than in the auth layer: code 21 is a
    generic invalid-parameter code Netatmo also answers `addwebhook` with, so
    only the caller that sent a home id can read it as a rejected home.
    """
    home_id = "91763b24c43d3e344f424e8b"
    message = "400 - Bad request - Invalid home_id (21) when accessing '/homestatus'"

    async def _rejected(*_args, **_kwargs):
        raise pyatmo.exceptions.ApiError(message, status=400, code=21)

    with (
        patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request", _rejected),
        pytest.raises(pyatmo.exceptions.InvalidHomeError) as exc_info,
    ):
        await async_account.async_update_status(home_id)

    assert str(exc_info.value) == message
    assert exc_info.value.code == 21
    assert exc_info.value.status == 400
    assert isinstance(exc_info.value.__cause__, pyatmo.exceptions.ApiError)


async def test_update_status_other_api_error_stays_generic(async_account):
    """Any other API failure passes through unchanged.

    Only code 21 means the home id was refused; everything else stays a plain
    ApiError so a caller does not stop polling a home over an unrelated fault.
    """
    home_id = "91763b24c43d3e344f424e8b"
    message = (
        "400 - Bad request - Invalid access token (2) when accessing '/homestatus'"
    )

    async def _rejected(*_args, **_kwargs):
        raise pyatmo.exceptions.ApiError(message, status=400, code=2)

    with (
        patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request", _rejected),
        pytest.raises(pyatmo.exceptions.ApiError) as exc_info,
    ):
        await async_account.async_update_status(home_id)

    assert not isinstance(exc_info.value, pyatmo.exceptions.InvalidHomeError)
    assert str(exc_info.value) == message


async def test_update_status_string_error_code_stays_generic(async_account):
    """A string error code is never read as the rejected-home code 21.

    ``webhooks/v1`` answers with string codes such as ``WH009`` while the
    ``api/*`` endpoints answer with integers, so an ``ApiError`` reaching this
    caller may carry either. A string equals no integer constant, so the error
    passes through untranslated and with its code intact.
    """
    home_id = "91763b24c43d3e344f424e8b"
    message = "409 - Conflict - webhook limit reached (WH009)"

    async def _rejected(*_args, **_kwargs):
        raise pyatmo.exceptions.ApiError(message, status=409, code="WH009")

    with (
        patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request", _rejected),
        pytest.raises(pyatmo.exceptions.ApiError) as exc_info,
    ):
        await async_account.async_update_status(home_id)

    assert not isinstance(exc_info.value, pyatmo.exceptions.InvalidHomeError)
    assert exc_info.value.code == "WH009"
    assert exc_info.value.code != INVALID_HOME_ERROR_CODE


def test_invalid_home_error_is_an_api_error():
    """Consumers catching ApiError keep catching this one.

    Home Assistant's `async_fetch_data` catches `ApiError`; anything else
    escapes and breaks its update loop.
    """
    assert issubclass(pyatmo.exceptions.InvalidHomeError, pyatmo.exceptions.ApiError)


async def test_update_events_body_less_response_names_the_home(async_account):
    """/getevents gets the same treatment as /homestatus."""
    home_id = "91763b24c43d3e344f424e8b"

    async def _body_less_response(*_args, **_kwargs):
        return MockResponse({"status": "ok", "time_server": 1786656837}, 200)

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            _body_less_response,
        ),
        pytest.raises(NoDeviceError) as exc_info,
    ):
        await async_account.async_update_events(home_id)

    assert f"for home {home_id}" in str(exc_info.value)


async def test_set_state_disabled_home_skips_call(async_auth, caplog):
    """A disabled home_id logs a warning and makes no API request."""
    account = pyatmo.AsyncAccount(async_auth, disabled_homes_ids=["home_disabled"])

    with caplog.at_level(logging.WARNING):
        await account.async_set_state("home_disabled", {"foo": "bar"})

    async_auth.async_post_api_request.assert_not_called()
    assert "home_disabled" in caplog.text


async def test_update_devices_names_the_device_it_cannot_place(
    async_account,
    caplog,
):
    """A device with no resolvable home is identified, not logged as None.

    Standalone weather and air-care devices legitimately reach this branch, so
    the line is expected traffic and must not be silenced -- but it named
    nothing, rendering as "None (None)" for every such device.
    """
    device_data = {"_id": "99:99:99:99:99:99", "type": "NAMain"}

    with caplog.at_level(logging.DEBUG, logger="pyatmo.account"):
        await async_account.update_devices({"devices": [device_data]})

    assert "99:99:99:99:99:99" in caplog.text
    assert "NAMain" in caplog.text
    assert "None (None)" not in caplog.text


async def test_update_devices_does_not_search_when_the_home_is_known(async_account):
    """The fallback search must not run for a device that names its home.

    ``NHC`` because the later standalone-device check short-circuits on that
    type; any other type would call ``find_home_of_device`` again from there,
    for the unrelated question of whether the device is a member of a home.
    """
    device_data = {
        "_id": "99:99:99:99:99:99",
        "type": "NHC",
        "home_id": "known_home",
        "home_name": "Known",
        "modules": [],
    }

    with patch.object(async_account, "find_home_of_device") as mock_find:
        await async_account.update_devices({"devices": [device_data]})

    mock_find.assert_not_called()


async def test_update_status_translates_a_string_error_code(async_account):
    """Netatmo is inconsistent about code types; both must translate."""
    message = "400 - Bad request - Invalid home_id (21)"

    async def _rejected(*_args, **_kwargs):
        raise pyatmo.exceptions.ApiError(message, status=400, code="21")

    with (
        patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request", _rejected),
        pytest.raises(pyatmo.exceptions.InvalidHomeError),
    ):
        await async_account.async_update_status("whatever")


async def test_update_status_ignores_code_21_from_another_status(async_account):
    """The contract is 400 plus code 21, not code 21 on any status."""
    message = "500 - Internal Server Error - (21)"

    async def _rejected(*_args, **_kwargs):
        raise pyatmo.exceptions.ApiError(message, status=500, code=21)

    with (
        patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request", _rejected),
        pytest.raises(pyatmo.exceptions.ApiError) as exc_info,
    ):
        await async_account.async_update_status("whatever")

    assert not isinstance(exc_info.value, pyatmo.exceptions.InvalidHomeError)


async def test_update_status_passes_through_an_invalid_home_error(async_account):
    """An InvalidHomeError from below is not wrapped in a second one."""
    original = pyatmo.exceptions.InvalidHomeError(
        "already specific",
        status=400,
        code=21,
    )

    async def _rejected(*_args, **_kwargs):
        raise original

    with (
        patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request", _rejected),
        pytest.raises(pyatmo.exceptions.InvalidHomeError) as exc_info,
    ):
        await async_account.async_update_status("whatever")

    assert exc_info.value is original
