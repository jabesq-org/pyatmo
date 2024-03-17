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
    #changed teh reference here as start and stop data was not calculated in the spirit of the netatmo api where their time data is in the fact representing the "middle" of the range and not the begining
    assert module.historical_data[0] == {'Wh': 197, 'duration': 60, 'endTime': '2022-02-05T08:59:49Z', 'endTimeUnix': 1644051589, 'energyMode': 'standard', 'startTime': '2022-02-05T07:59:50Z', 'startTimeUnix': 1644047989}
    assert module.historical_data[-1] == {'Wh': 259, 'duration': 60, 'endTime': '2022-02-12T07:59:49Z', 'endTimeUnix': 1644652789, 'energyMode': 'standard', 'startTime': '2022-02-12T06:59:50Z', 'startTimeUnix': 1644649189}
    assert len(module.historical_data) == 168



async def test_historical_data_retrieval_multi(async_account_multi):
    """Test retrieval of historical measurements."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"

    home = async_account_multi.homes[home_id]

    module_id = "98:76:54:32:10:00:00:73"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NLC

    strt =  1709421000
    end_time = 1709679599

    strt = int(dt.datetime.fromisoformat("2024-03-03 00:10:00").timestamp())
    end_time = int(dt.datetime.fromisoformat("2024-03-05 23:59:59").timestamp())

    await async_account_multi.async_update_measures(home_id=home_id,
                                                    module_id=module_id,
                                                    interval=MeasureInterval.HALF_HOUR,
                                                    start_time=strt,
                                                    end_time=end_time
                                                    )


    assert module.historical_data[0] == {'Wh': 0, 'duration': 30, 'endTime': '2024-03-02T23:40:00Z', 'endTimeUnix': 1709422800, 'energyMode': 'peak', 'startTime': '2024-03-02T23:10:01Z', 'startTimeUnix': 1709421000}
    assert module.historical_data[-1] == {'Wh': 0, 'duration': 30, 'endTime': '2024-03-05T23:10:00Z', 'endTimeUnix': 1709680200, 'energyMode': 'peak', 'startTime': '2024-03-05T22:40:01Z', 'startTimeUnix': 1709678400}
    assert len(module.historical_data) == 134

    assert module.sum_energy_elec == module.sum_energy_elec_peak + module.sum_energy_elec_off_peak
    assert module.sum_energy_elec_off_peak == 11219
    assert module.sum_energy_elec_peak == 31282






async def test_historical_data_retrieval_multi_2(async_account_multi):
    """Test retrieval of historical measurements."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"

    home = async_account_multi.homes[home_id]

    module_id = "98:76:54:32:10:00:00:49"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NLC




    strt = int(dt.datetime.fromisoformat("2024-03-15 00:29:51").timestamp())
    end = int(dt.datetime.fromisoformat("2024-03-15 13:45:24").timestamp())

    await async_account_multi.async_update_measures(home_id=home_id,
                                                    module_id=module_id,
                                                    interval=MeasureInterval.HALF_HOUR,
                                                    start_time=strt,
                                                    end_time=end
                                                    )


    assert module.historical_data[0] == {'Wh': 0, 'duration': 30, 'endTime': '2024-03-14T23:59:51Z', 'endTimeUnix': 1710460791, 'energyMode': 'peak', 'startTime': '2024-03-14T23:29:52Z', 'startTimeUnix': 1710458991}
    assert module.historical_data[-1] == {'Wh': 0, 'duration': 30, 'endTime': '2024-03-15T12:59:51Z', 'endTimeUnix': 1710507591, 'energyMode': 'peak', 'startTime': '2024-03-15T12:29:52Z', 'startTimeUnix': 1710505791}
    assert len(module.historical_data) == 26

    assert module.sum_energy_elec == module.sum_energy_elec_peak + module.sum_energy_elec_off_peak
    assert module.sum_energy_elec_off_peak == 780
    assert module.sum_energy_elec_peak == 890


    sum = async_account_multi.get_current_energy_sum()

    assert module.sum_energy_elec == sum
