"""Define tests for energy module."""

from pyatmo import DeviceType
import pytest

import time_machine
import datetime as dt

from pyatmo.const import MeasureInterval


# pylint: disable=F6401


@pytest.mark.asyncio
async def test_async_energy_NLPC(async_home):  # pylint: disable=invalid-name
    """Test Legrand / BTicino connected energy meter module."""
    module_id = "12:34:56:00:00:a1:4c:da"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLPC
    assert module.power == 476

@time_machine.travel(dt.datetime(2022, 2, 12, 7, 59, 49))
@pytest.mark.asyncio
async def test_historical_data_retrieval(async_account):
    """Test retrieval of historical measurements."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_events(home_id=home_id)
    home = async_account.homes[home_id]

    module_id = "12:34:56:00:00:a1:4c:da"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NLPC

    await async_account.async_update_measures(home_id=home_id, module_id=module_id)
    assert module.historical_data[0] == {
        "Wh": 197,
        "duration": 60,
        "startTime": "2022-02-05T08:29:50Z",
        "endTime": "2022-02-05T09:29:49Z",
        "endTimeUnix": 1644053389,
        "startTimeUnix": 1644049789,
        "energyMode": "standard"
    }
    assert module.historical_data[-1] == {
        "Wh": 259,
        "duration": 60,
        "startTime": "2022-02-12T07:29:50Z",
        "startTimeUnix": 1644650989,
        "endTime": "2022-02-12T08:29:49Z",
        "endTimeUnix": 1644654589,
        "energyMode": "standard"
    }
    assert len(module.historical_data) == 168



async def test_historical_data_retrieval_multi(async_account_multi):
    """Test retrieval of historical measurements."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"

    home = async_account_multi.homes[home_id]

    module_id = "98:76:54:32:10:00:00:73"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NLC

    strt = 1709421900 #1709421000+15*60
    await async_account_multi.async_update_measures(home_id=home_id,
                                                    module_id=module_id,
                                                    interval=MeasureInterval.HALF_HOUR,
                                                    start_time=strt,
                                                    end_time=1709679599
                                                    )


    assert module.historical_data[0] == {'Wh': 0, 'duration': 30, 'endTime': '2024-03-02T23:55:00Z', 'endTimeUnix': 1709423700, 'energyMode': 'peak', 'startTime': '2024-03-02T23:25:01Z', 'startTimeUnix': strt}
    assert module.historical_data[-1] == {'Wh': 0, 'duration': 30, 'endTime': '2024-03-05T20:55:00Z', 'endTimeUnix': 1709672100, 'energyMode': 'peak', 'startTime': '2024-03-05T20:25:01Z', 'startTimeUnix': 1709670300}
    assert len(module.historical_data) == 134

    assert module.sum_energy_elec == module.sum_energy_elec_peak + module.sum_energy_elec_off_peak
    assert module.sum_energy_elec_off_peak == 11219
    assert module.sum_energy_elec_peak == 31282


