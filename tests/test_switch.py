"""Define tests for switch module."""

import pytest

from pyatmo import DeviceType

# pylint: disable=F6401


@pytest.mark.asyncio()
async def test_async_switch_NLP(async_home):  # pylint: disable=invalid-name
    """Test NLP Legrand plug."""
    module_id = "12:34:56:80:00:12:ac:f2"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLP
    assert module.firmware_revision == 62
    assert module.on
    assert module.power == 0


@pytest.mark.asyncio()
async def test_async_switch_NLF(async_home):  # pylint: disable=invalid-name
    """Test NLF Legrand dimmer."""
    module_id = "00:11:22:33:00:11:45:fe"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLF
    assert module.firmware_revision == 57
    assert module.on is False
    assert module.brightness == 63
    assert module.power == 0
