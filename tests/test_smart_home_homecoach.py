"""Define tests for HomeCoach module."""
import json

import pytest

from freezegun import freeze_time

from .conftest import does_not_raise

import smart_home.HomeCoach


def test_HomeCoachData(homeCoachData):
    assert homeCoachData.default_station == "Bedroom"


@pytest.mark.parametrize(
    "station, expected",
    [
        (
            None,
            [
                "Bedroom",
                "Kitchen",
                "Livingroom",
            ],
        ),
        (
            "Bedroom",
            [
                "Bedroom",
                "Kitchen",
                "Livingroom",
            ],
        ),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.skip("Invalid station names are not handled yet."),
        ),
    ],
)
def test_HomeCoachData_modulesNamesList(homeCoachData, station, expected):
    assert sorted(homeCoachData.modulesNamesList(station)) == expected

