"""Define tests for fan module."""

import pytest

from pyatmo import DeviceType

# pylint: disable=F6401


@pytest.mark.asyncio()
async def test_async_fan_NLLF(async_home):  # pylint: disable=invalid-name
    """Test NLLF Legrand centralized ventilation controller."""
    module_id = "12:34:56:00:01:01:01:b1"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLLF
    assert module.power == 11
    assert module.firmware_revision == 60
    assert module.fan_speed == 1
