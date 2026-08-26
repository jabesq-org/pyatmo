"""Define tests for BTicino MyHome Server 1 (MHS1) shutter capabilities."""

from pyatmo import DeviceType


async def test_async_shutter_bnas_uncalibrated(async_home_bticino):
    """An actor reporting target_position:step 100 only supports open/close/stop."""
    module = async_home_bticino.modules["bticino_shutter_uncalibrated"]
    assert module.device_type == DeviceType.BNAS
    assert module.target_position__step == 100
    assert module.current_position == 101
    assert module.can_set_target_position is False
    assert module.can_report_position is False
    assert module.can_move_to_preferred_position is False


async def test_async_shutter_bnas_calibrated(async_home_bticino):
    """An actor reporting a step below 100 is calibrated for exact positioning."""
    module = async_home_bticino.modules["bticino_shutter_calibrated"]
    assert module.device_type == DeviceType.BNAS
    assert module.target_position__step == 5
    assert module.current_position == 42
    assert module.can_set_target_position is True
    assert module.can_report_position is True
    assert module.can_move_to_preferred_position is False


async def test_async_shutter_bnas_step_survives_topology_update(
    async_account_bticino,
    async_home_bticino,
):
    """A /homesdata refresh carries no step and must not drop the known one."""
    module = async_home_bticino.modules["bticino_shutter_calibrated"]
    assert module.can_set_target_position is True

    await async_account_bticino.async_update_topology()

    assert module.target_position__step == 5
    assert module.can_set_target_position is True
    assert module.can_report_position is True


async def test_async_shutter_bnas_unknown_step(async_home_bticino):
    """An actor with no reported step is treated as not positionable."""
    module = async_home_bticino.modules["bticino_shutter_calibrated"]
    module.target_position__step = None
    assert module.can_set_target_position is False
    assert module.can_report_position is False
    assert module.can_move_to_preferred_position is False


async def test_async_shutter_bnab_calibrated(async_home_bticino):
    """BNAB reaches the mixin via Shutter and is calibrated for exact positioning."""
    module = async_home_bticino.modules["bticino_blind_calibrated"]
    assert module.device_type == DeviceType.BNAB
    assert module.target_position__step == 5
    assert module.current_position == 30
    assert module.can_set_target_position is True
    assert module.can_report_position is True
    assert module.can_move_to_preferred_position is False


async def test_async_shutter_bnms_uncalibrated(async_home_bticino):
    """BNMS reaches the mixin via Shutter and only supports open/close/stop."""
    module = async_home_bticino.modules["bticino_shade_uncalibrated"]
    assert module.device_type == DeviceType.BNMS
    assert module.target_position__step == 100
    assert module.current_position == 101
    assert module.can_set_target_position is False
    assert module.can_report_position is False
    assert module.can_move_to_preferred_position is False
