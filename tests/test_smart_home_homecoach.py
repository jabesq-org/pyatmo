"""Define tests for HomeCoach module."""
import pytest


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
