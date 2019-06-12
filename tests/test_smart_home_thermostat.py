"""Define tests for Thermostat module."""
import json

import pytest

import smart_home.Thermostat

from contextlib import contextmanager


@contextmanager
def does_not_raise():
    yield


def test_HomeData(homeData):
    assert homeData.default_home == "MYHOME"
    assert len(homeData.rooms[homeData.default_home]) == 2

    assert len(homeData.modules[homeData.default_home]) == 3

    expected = {
        "12:34:56:00:fa:d0": {
            "id": "12:34:56:00:fa:d0",
            "type": "NAPlug",
            "name": "Thermostat",
            "setup_date": 1494963356,
            "modules_bridged": ["12:34:56:00:01:ae"],
        },
        "12:34:56:00:01:ae": {
            "id": "12:34:56:00:01:ae",
            "type": "NATherm1",
            "name": "Livingroom",
            "setup_date": 1494963356,
            "room_id": "2746182631",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:00:f1:62": {
            "id": "12:34:56:00:f1:62",
            "type": "NACamera",
            "name": "Hall",
            "setup_date": 1544828430,
            "room_id": "3688132631",
        },
    }
    assert homeData.modules[homeData.default_home] == expected


def test_HomeData_noData(auth, requests_mock):
    requests_mock.post(smart_home.Thermostat._GETHOMESDATA_REQ, text="None")
    with pytest.raises(smart_home.PublicData.NoDevice):
        assert smart_home.Thermostat.HomeData(auth)


def test_HomeData_noBody(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.Thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.PublicData.NoDevice):
        assert smart_home.Thermostat.HomeData(auth)


def test_HomeData_noHomeName(auth, requests_mock):
    with open("fixtures/home_data_nohomename.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.Thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.PublicData.NoDevice):
        assert smart_home.Thermostat.HomeData(auth)


def test_HomeData_homeById(homeData):
    home_id = "91763b24c43d3e344f424e8b"
    assert homeData.homeById(home_id)["name"] == "MYHOME"


def test_HomeData_homeByName(homeData):
    assert homeData.homeByName()["name"] == "MYHOME"


def test_HomeData_gethomeId(homeData):
    assert homeData.gethomeId() == "91763b24c43d3e344f424e8b"


def test_HomeData_getSelectedschedule(homeData):
    assert homeData.getSelectedschedule()["name"] == "Default"


@pytest.mark.parametrize(
    "t_home, t_sched_id, t_sched, expected",
    [
        (None, None, None, pytest.raises(smart_home.Thermostat.NoSchedule)),
        (None, None, "Default", does_not_raise()),
        (None, "591b54a2764ff4d50d8b5795", None, does_not_raise()),
    ],
)
def test_HomeData_switchHomeSchedule(
    homeData, requests_mock, t_home, t_sched_id, t_sched, expected
):
    with open("fixtures/status_ok.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.Thermostat._SWITCHHOMESCHEDULE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with expected:
        homeData.switchHomeSchedule(
            schedule_id=t_sched_id, schedule=t_sched, home=t_home
        )


def test_HomeStatus(homeStatus):
    assert len(homeStatus.rooms) == 1
    assert homeStatus.default_room["id"] == "2746182631"

    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert homeStatus.default_room == expexted


def test_HomeStatus_roomById(homeStatus):
    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert homeStatus.roomById("2746182631") == expexted


def test_HomeStatus_thermostatById(homeStatus):
    expexted = {
        "id": "12:34:56:00:01:ae",
        "reachable": True,
        "type": "NATherm1",
        "firmware_revision": 65,
        "rf_strength": 58,
        "battery_level": 3793,
        "boiler_valve_comfort_boost": False,
        "boiler_status": False,
        "anticipating": False,
        "bridge": "12:34:56:00:fa:d0",
        "battery_state": "high",
    }
    assert homeStatus.thermostatById("12:34:56:00:01:ae") == expexted


def test_HomeStatus_relayById(homeStatus):
    expexted = {
        "id": "12:34:56:00:fa:d0",
        "type": "NAPlug",
        "firmware_revision": 174,
        "rf_strength": 107,
        "wifi_strength": 42,
    }
    assert homeStatus.relayById("12:34:56:00:fa:d0") == expexted


def test_HomeStatus_setPoint(homeStatus):
    assert homeStatus.setPoint("2746182631") == 12


def test_HomeStatus_setPointmode(homeStatus):
    assert homeStatus.setPointmode("2746182631") == "away"


def test_HomeStatus_getAwaytemp(homeStatus):
    assert homeStatus.getAwaytemp() == 14


def test_HomeStatus_getHgtemp(homeStatus):
    assert homeStatus.getHgtemp() == 7


def test_HomeStatus_measuredTemperature(homeStatus):
    assert homeStatus.measuredTemperature() == 19.8


def test_HomeStatus_boilerStatus(homeStatus):
    assert homeStatus.boilerStatus() is False


def test_HomeStatus_thermostatType(homeStatus, homeData):
    assert homeStatus.thermostatType("MYHOME", "2746182631") == "NATherm1"
