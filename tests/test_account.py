"""Define tests for the account module."""

from pyatmo import modules


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
