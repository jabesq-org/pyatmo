"""Define tests for WeatherStation module."""
import json

import pytest

from .conftest import does_not_raise

import smart_home.WeatherStation


def test_WeatherStationData(weatherStationData):
    assert weatherStationData.default_station == "MyStation"


def test_WeatherStationData_no_response(auth, requests_mock):
    requests_mock.post(smart_home.WeatherStation._GETSTATIONDATA_REQ, text="None")
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.WeatherStation.WeatherStationData(auth)


def test_WeatherStationData_no_body(auth, requests_mock):
    with open("fixtures/status_ok.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.WeatherStation._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.WeatherStation.WeatherStationData(auth)


def test_WeatherStationData_no_data(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.WeatherStation._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.WeatherStation.WeatherStationData(auth)
