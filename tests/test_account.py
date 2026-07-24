"""Define tests for the account module."""

from unittest.mock import patch

import pyatmo
from pyatmo import modules

from .common import fake_post_request


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


DISABLED_HOME_ID = "91763b24c43d3e344f424e8b"


async def test_update_devices_skips_disabled_homes(async_account_disabled_home):
    """Test that device updates do not re-create a disabled home.

    ``process_topology`` prunes disabled homes from ``homes``, but
    ``update_devices`` used to re-create them as pseudo-homes when a weather
    station reported the disabled ``home_id`` (getstationsdata still returns
    every device of the account).
    """
    account = async_account_disabled_home
    disabled_home_station_id = "12:34:56:80:bb:26"
    homeless_station_id = "12:34:56:37:11:ca"

    assert DISABLED_HOME_ID in account.all_homes_id

    # The "MYHOME (Palier)" station reports the disabled home_id
    await account.async_update_weather_stations()

    assert DISABLED_HOME_ID not in account.homes
    assert disabled_home_station_id not in account.modules
    # Stations without a home are still processed account wide
    assert homeless_station_id in account.modules

    # The selection survives another topology and weather round
    await account.async_update_topology(disabled_homes_ids=[DISABLED_HOME_ID])
    await account.async_update_weather_stations()

    assert DISABLED_HOME_ID not in account.homes


async def test_update_devices_skips_disabled_home_coach(async_account_disabled_home):
    """Test that a home coach reporting a disabled home is skipped.

    Real ``gethomecoachsdata`` payloads usually carry no ``home_id``; such
    devices cannot be attributed to any home and stay account scoped. This
    covers the payloads that do report one.
    """
    account = async_account_disabled_home
    home_coach_id = "00:11:22:33:44:66"

    await account.update_devices(
        {
            "devices": [
                {"_id": home_coach_id, "type": "NHC", "home_id": DISABLED_HOME_ID},
            ],
        },
    )

    assert DISABLED_HOME_ID not in account.homes
    assert home_coach_id not in account.modules


async def test_process_topology_prunes_unknown_disabled_home(async_auth):
    """Test disabling prunes a pseudo-home absent from the raw topology."""
    foreign_home_id = "aaaaaaaaaaaaaaaaaaaaaaaa"

    account = pyatmo.AsyncAccount(async_auth)
    await account.update_devices(
        {
            "devices": [
                {
                    "_id": "aa:bb:cc:dd:ee:ff",
                    "type": "NAMain",
                    "home_id": foreign_home_id,
                },
            ],
        },
    )

    assert foreign_home_id in account.homes

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_post_request,
    ):
        await account.async_update_topology(disabled_homes_ids=[foreign_home_id])

    assert foreign_home_id not in account.homes


async def test_update_topology_clears_disabled_homes(async_account_disabled_home):
    """Test a topology refresh without disabled homes re-enables them."""
    account = async_account_disabled_home

    await account.async_update_topology()

    assert not account.disabled_homes_ids
    assert DISABLED_HOME_ID in account.homes
