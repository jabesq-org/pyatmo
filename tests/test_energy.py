"""Define tests for climate module."""

from pyatmo import DeviceType
import pytest

# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_energy_NLPC(async_home):  # pylint: disable=invalid-name
    """Test Legrand / BTicino connected energy meter module."""
    module_id = "12:34:56:00:00:a1:4c:da"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLPC
    assert module.power == 476
