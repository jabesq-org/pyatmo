"""Define tests for switch module."""

from pyatmo import DeviceType
from pyatmo.modules.device_types import DeviceCategory


async def test_async_switch_NLP(async_home):
    """Test NLP Legrand plug."""
    module_id = "12:34:56:80:00:12:ac:f2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLP
    assert module.firmware_revision == 62
    assert module.on
    assert module.power == 0


async def test_async_switch_NLF(async_home):
    """Test NLF Legrand dimmer."""
    module_id = "00:11:22:33:00:11:45:fe"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLF
    assert module.firmware_revision == 57
    assert module.on is False
    assert module.brightness == 63
    assert module.power == 0


async def test_async_switch_NLIS(async_home):
    """Test NLIS Legrand module."""
    module_id = "12:34:56:00:01:01:01:b6"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_category is None
    module_id = "12:34:56:00:01:01:01:b6#1"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_category == DeviceCategory.switch
    module_id = "12:34:56:00:01:01:01:b6#2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_category == DeviceCategory.switch
