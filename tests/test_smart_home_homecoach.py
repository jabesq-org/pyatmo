"""Define tests for HomeCoach module."""
import json

import pytest

import smart_home.HomeCoach


def test_HomeCoachData(homeCoachData):
    assert homeCoachData.default_station == "Bedroom"


@pytest.mark.parametrize(
    "station, expected",
    [
        (None, ["Bedroom", "Indoor", "Kitchen", "Livingroom"]),
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


@pytest.mark.parametrize(
    "station, expected",
    [
        (
            None,
            {
                "12:34:56:26:69:0c": {
                    "station_name": "Bedroom",
                    "module_name": "Bedroom",
                    "id": "12:34:56:26:69:0c",
                },
                "12:34:56:25:cf:a8": {
                    "station_name": "Kitchen",
                    "module_name": "Kitchen",
                    "id": "12:34:56:25:cf:a8",
                },
                "12:34:56:26:65:14": {
                    "station_name": "Livingroom",
                    "module_name": "Livingroom",
                    "id": "12:34:56:26:65:14",
                },
                "12:34:56:3e:c5:46": {
                    "station_name": "Parents Bedroom",
                    "module_name": "Indoor",
                    "id": "12:34:56:3e:c5:46",
                },
                "12:34:56:26:68:92": {
                    "station_name": "Baby Bedroom",
                    "module_name": "Indoor",
                    "id": "12:34:56:26:68:92",
                },
            },
        ),
        (
            "Bedroom",
            {
                "12:34:56:26:69:0c": {
                    "station_name": "Bedroom",
                    "module_name": "Bedroom",
                    "id": "12:34:56:26:69:0c",
                }
            },
        ),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet."
            ),
        ),
    ],
)
def test_HomeCoachData_getModules(homeCoachData, station, expected):
    assert homeCoachData.getModules(station) == expected


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
