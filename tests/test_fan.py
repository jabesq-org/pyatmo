"""Define tests for fan module."""

from pyatmo import DeviceType


async def test_async_fan_NLLF(async_home):
    """Test NLLF Legrand centralized ventilation controller."""
    module_id = "12:34:56:00:01:01:01:b1"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLLF
    assert module.power == 11
    assert module.firmware_revision == 60
    assert module.fan_speed == 1
