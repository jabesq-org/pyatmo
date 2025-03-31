"""Define tests for energy module."""

import datetime as dt
import json
from unittest.mock import patch

import pytest
import time_machine

from pyatmo import ApiHomeReachabilityError, DeviceType
from pyatmo.modules.module import EnergyHistoryMixin, MeasureInterval
from tests.common import MockResponse

# pylint: disable=F6401


@pytest.mark.asyncio()
async def test_async_energy_NLPC(async_home):  # pylint: disable=invalid-name
    """Test Legrand / BTicino connected energy meter module."""
    module_id = "12:34:56:00:00:a1:4c:da"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NLPC
    assert module.power == 476


@time_machine.travel(dt.datetime(2022, 2, 12, 7, 59, 49))
@pytest.mark.asyncio()
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
    # changed the reference here as start and stop data was not calculated in the spirit of the netatmo api where their time data is in the fact representing the "middle" of the range and not the begining
    assert module.historical_data[0] == {
        "Wh": 197,
        "duration": 60,
        "endTime": "2022-02-05T08:59:49Z",
        "endTimeUnix": 1644051589,
        "energyMode": ["basic"],
        "WhPerModes": [197],
        "startTime": "2022-02-05T07:59:50Z",
        "startTimeUnix": 1644047989,
    }
    assert module.historical_data[-1] == {
        "Wh": 259,
        "duration": 60,
        "endTime": "2022-02-12T07:59:49Z",
        "endTimeUnix": 1644652789,
        "energyMode": ["basic"],
        "WhPerModes": [259],
        "startTime": "2022-02-12T06:59:50Z",
        "startTimeUnix": 1644649189,
    }
    assert len(module.historical_data) == 168


@time_machine.travel(dt.datetime(2024, 7, 24, 22, 00, 10))
@pytest.mark.asyncio()
async def test_historical_data_retrieval_multi(async_account_multi):
    """Test retrieval of historical measurements."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"

    home = async_account_multi.homes[home_id]

    module_id = "98:76:54:32:10:00:00:69"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NLPC

    strt = int(dt.datetime.fromisoformat("2024-07-24 00:00:00").timestamp())
    end_time = int(dt.datetime.fromisoformat("2024-07-24 22:27:00").timestamp())

    await async_account_multi.async_update_measures(
        home_id=home_id,
        module_id=module_id,
        interval=MeasureInterval.HALF_HOUR,
        start_time=strt,
        end_time=end_time,
    )
    assert isinstance(module, EnergyHistoryMixin)

    assert module.historical_data[0] == {
        "Wh": 20,
        "duration": 30,
        "endTime": "2024-07-23T22:30:00Z",
        "endTimeUnix": 1721773800,
        "energyMode": ["basic"],
        "WhPerModes": [20],
        "startTime": "2024-07-23T22:00:01Z",
        "startTimeUnix": 1721772000,
    }
    assert module.historical_data[17] == {
        "Wh": 710,
        "WhPerModes": [498, 212],
        "duration": 30,
        "endTime": "2024-07-24T07:00:00Z",
        "endTimeUnix": 1721804400,
        "energyMode": ["basic", "peak"],
        "startTime": "2024-07-24T06:30:01Z",
        "startTimeUnix": 1721802600,
    }

    assert module.historical_data[-1] == {
        "Wh": 16,
        "WhPerModes": [16],
        "duration": 30,
        "endTime": "2024-07-24T17:30:00Z",
        "endTimeUnix": 1721842200,
        "energyMode": ["peak"],
        "startTime": "2024-07-24T17:00:01Z",
        "startTimeUnix": 1721840400,
    }

    assert len(module.historical_data) == 39
    assert module.sum_energy_elec == 17547
    assert module.sum_energy_elec_off_peak == 4290
    assert module.sum_energy_elec_peak == 10177


@patch("pyatmo.auth.AbstractAsyncAuth.async_post_api_request")
async def test_disconnected_main_bridge(mock_home_status, async_account_multi):
    """Test retrieval of historical measurements."""
    home_id = "aaaaaaaaaaabbbbbbbbbbccc"

    with open(
        "fixtures/home_multi_status_error_disconnected.json",
        encoding="utf-8",
    ) as json_file:
        home_status_fixture = json.load(json_file)
    mock_home_status_resp = MockResponse(home_status_fixture, 200)
    mock_home_status.return_value = mock_home_status_resp

    with pytest.raises(ApiHomeReachabilityError):
        await async_account_multi.async_update_status(home_id)
