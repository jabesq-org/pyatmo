"""Define tests for HomeCoach module."""
# pylint: disable=protected-access
import json

import pytest

import pyatmo


def test_home_coach_data(home_coach_data):
    assert home_coach_data.default_station == "Bedroom"


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
def test_home_coach_data_modules_names_list(home_coach_data, station, expected):
    assert sorted(home_coach_data.modules_names_list(station)) == expected


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
def test_home_coach_data_get_modules(home_coach_data, station, expected):
    assert home_coach_data.get_modules(station) == expected


def test_home_coach_data_no_devices(auth, requests_mock):
    with open("fixtures/home_coach_no_devices.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.home_coach._GETHOMECOACHDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.home_coach.HomeCoachData(auth)
