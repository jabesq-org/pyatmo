"""Define tests for HomeCoach module."""
import json

import pytest

import smart_home.HomeCoach


def test_HomeCoachData(homeCoachData):
    assert homeCoachData.default_station == "Bedroom"


@pytest.mark.parametrize(
    "station, expected",
    [
        (None, ["Bedroom", "Kitchen", "Livingroom"]),
        ("Bedroom", ["Bedroom"]),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet."
            ),
        ),
    ],
)
def test_HomeCoachData_modulesNamesList(homeCoachData, station, expected):
    assert sorted(homeCoachData.modulesNamesList(station)) == expected


def test_HomeCoachData_no_devices(auth, requests_mock):
    with open("fixtures/home_coach_no_devices.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.HomeCoach._GETHOMECOACHDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.HomeCoach.HomeCoachData(auth)
