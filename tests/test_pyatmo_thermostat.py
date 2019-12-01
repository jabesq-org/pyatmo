"""Define tests for Thermostat module."""
import json

import pytest

import pyatmo

from .conftest import does_not_raise


def test_HomeData(homeData):
    assert homeData.default_home == "MYHOME"
    assert homeData.default_home_id == "91763b24c43d3e344f424e8b"
    assert len(homeData.rooms[homeData.default_home_id]) == 4

    assert len(homeData.modules[homeData.default_home_id]) == 5

    expected = {
        "12:34:56:00:fa:d0": {
            "id": "12:34:56:00:fa:d0",
            "type": "NAPlug",
            "name": "Thermostat",
            "setup_date": 1494963356,
            "modules_bridged": [
                "12:34:56:00:01:ae",
                "12:34:56:03:a0:ac",
                "12:34:56:03:a5:54",
            ],
        },
        "12:34:56:00:01:ae": {
            "id": "12:34:56:00:01:ae",
            "type": "NATherm1",
            "name": "Livingroom",
            "setup_date": 1494963356,
            "room_id": "2746182631",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:03:a5:54": {
            "id": "12:34:56:03:a5:54",
            "type": "NRV",
            "name": "Valve1",
            "setup_date": 1554549767,
            "room_id": "2833524037",
            "bridge": "12:34:56:00:fa:d0",
        },
        "12:34:56:03:a0:ac": {
            "id": "12:34:56:03:a0:ac",
            "type": "NRV",
            "name": "Valve2",
            "setup_date": 1554554444,
            "room_id": "2940411577",
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
    assert homeData.modules[homeData.default_home_id] == expected


def test_HomeData_no_data(auth, requests_mock):
    requests_mock.post(pyatmo.thermostat._GETHOMESDATA_REQ, text="None")
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.HomeData(auth)


def test_HomeData_no_body(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.HomeData(auth)


def test_HomeData_no_home_name(auth, requests_mock):
    with open("fixtures/home_data_nohomename.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    homeData = pyatmo.HomeData(auth)
    home_id = "91763b24c43d3e344f424e8b"
    assert homeData.homeById(home_id)["name"] == "Unknown"


def test_HomeData_homeById(homeData):
    home_id = "91763b24c43d3e344f424e8b"
    assert homeData.homeById(home_id)["name"] == "MYHOME"
    home_id = "91763b24c43d3e344f424e8c"
    assert homeData.homeById(home_id)["name"] == "Unknown"


def test_HomeData_homeByName(homeData):
    assert homeData.homeByName()["name"] == "MYHOME"
    assert homeData.homeByName()["id"] == "91763b24c43d3e344f424e8b"


def test_HomeData_gethomeId(homeData):
    assert homeData.gethomeId() == "91763b24c43d3e344f424e8b"
    assert homeData.gethomeId("MYHOME") == "91763b24c43d3e344f424e8b"
    with pytest.raises(pyatmo.InvalidHome):
        assert homeData.gethomeId("InvalidName")


def test_HomeData_getHomeName(homeData):
    assert homeData.getHomeName() == "MYHOME"
    home_id = "91763b24c43d3e344f424e8b"
    assert homeData.getHomeName(home_id) == "MYHOME"
    home_id = "91763b24c43d3e344f424e8c"
    assert homeData.getHomeName(home_id) == "Unknown"


def test_HomeData_getSelectedschedule(homeData):
    assert homeData.getSelectedschedule()["name"] == "Default"
    assert homeData.getSelectedschedule("MYHOME")["name"] == "Default"
    with pytest.raises(pyatmo.InvalidHome):
        assert homeData.getSelectedschedule("Unknown")


@pytest.mark.parametrize(
    "t_home, t_sched_id, t_sched, expected",
    [
        (None, None, None, pytest.raises(pyatmo.NoSchedule)),
        (None, None, "Default", does_not_raise()),
        (None, "591b54a2764ff4d50d8b5795", None, does_not_raise()),
        (None, None, "Summer", pytest.raises(pyatmo.NoSchedule)),
        (None, "123456789abcdefg12345678", None, pytest.raises(pyatmo.NoSchedule)),
    ],
)
def test_HomeData_switchHomeSchedule(
    homeData, requests_mock, t_home, t_sched_id, t_sched, expected
):
    with open("fixtures/status_ok.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._SWITCHHOMESCHEDULE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with expected:
        homeData.switchHomeSchedule(
            schedule_id=t_sched_id, schedule=t_sched, home=t_home
        )


def test_HomeStatus(homeStatus):
    assert len(homeStatus.rooms) == 3
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


def test_HomeStatus_error_and_data(auth, requests_mock):
    with open("fixtures/home_status_error_and_data.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    homeStatus = pyatmo.HomeStatus(auth)
    assert len(homeStatus.rooms) == 3
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


def test_HomeStatus_error(auth, requests_mock):
    with open("fixtures/home_status_empty.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.HomeStatus(auth)


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
    with pytest.raises(pyatmo.InvalidRoom):
        assert homeStatus.roomById("0000000000")


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
    with pytest.raises(pyatmo.InvalidRoom):
        assert homeStatus.thermostatById("00:00:00:00:00:00")


def test_HomeStatus_relayById(homeStatus):
    expexted = {
        "id": "12:34:56:00:fa:d0",
        "type": "NAPlug",
        "firmware_revision": 174,
        "rf_strength": 107,
        "wifi_strength": 42,
    }
    assert homeStatus.relayById("12:34:56:00:fa:d0") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert homeStatus.relayById("00:00:00:00:00:00")


def test_HomeStatus_valveById(homeStatus):
    expexted = {
        "id": "12:34:56:03:a5:54",
        "reachable": True,
        "type": "NRV",
        "firmware_revision": 79,
        "rf_strength": 51,
        "battery_level": 3025,
        "bridge": "12:34:56:00:fa:d0",
        "battery_state": "full",
    }
    assert homeStatus.valveById("12:34:56:03:a5:54") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert homeStatus.valveById("00:00:00:00:00:00")


def test_HomeStatus_setPoint(homeStatus):
    assert homeStatus.setPoint() == 12
    assert homeStatus.setPoint("2746182631") == 12
    with pytest.raises(pyatmo.InvalidRoom):
        assert homeStatus.setPoint("0000000000")


def test_HomeStatus_setPointmode(homeStatus):
    assert homeStatus.setPointmode() == "away"
    assert homeStatus.setPointmode("2746182631") == "away"
    assert homeStatus.setPointmode("0000000000") is None


def test_HomeStatus_getAwaytemp(homeStatus):
    assert homeStatus.getAwaytemp() == 14
    assert homeStatus.getAwaytemp("MYHOME") == 14
    assert homeStatus.getAwaytemp("InvalidName") is None
    assert homeStatus.getAwaytemp(home_id="91763b24c43d3e344f424e8b") == 14
    assert homeStatus.getAwaytemp(home_id="00000000000000000000000") is None


def test_HomeStatus_getHgtemp(homeStatus):
    assert homeStatus.getHgtemp() == 7
    assert homeStatus.getHgtemp("MYHOME") == 7
    with pytest.raises(pyatmo.InvalidHome):
        assert homeStatus.getHgtemp("InvalidHome")
    assert homeStatus.getHgtemp(home_id="91763b24c43d3e344f424e8b") == 7
    assert homeStatus.getHgtemp(home_id="00000000000000000000000") is None


def test_HomeStatus_measuredTemperature(homeStatus):
    assert homeStatus.measuredTemperature() == 19.8
    assert homeStatus.measuredTemperature("2746182631") == 19.8
    with pytest.raises(pyatmo.InvalidRoom):
        assert homeStatus.measuredTemperature("0000000000")


def test_HomeStatus_boilerStatus(homeStatus):
    assert homeStatus.boilerStatus() is False


def test_HomeStatus_thermostatType(homeStatus):
    assert homeStatus.thermostatType("MYHOME", "2746182631") == "NATherm1"
    assert homeStatus.thermostatType("MYHOME", "2833524037") == "NRV"
    with pytest.raises(pyatmo.InvalidHome):
        assert homeStatus.thermostatType("InvalidHome", "2833524037")
    assert homeStatus.thermostatType("MYHOME", "0000000000") is None


@pytest.mark.parametrize(
    "home_id, mode, json_fixture, expected",
    [
        (None, None, "home_status_error_mode_is_missing.json", "mode is missing"),
        (
            "91763b24c43d3e344f424e8b",
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
        ),
        ("invalidID", "away", "home_status_error_invalid_id.json", "Invalid id"),
        ("91763b24c43d3e344f424e8b", "away", "status_ok.json", "ok"),
    ],
)
def test_HomeData_setThermmode(
    homeStatus, requests_mock, caplog, home_id, mode, json_fixture, expected
):
    with open("fixtures/%s" % json_fixture) as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._SETTHERMMODE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    res = homeStatus.setThermmode(home_id=home_id, mode=mode)
    if "error" in res:
        assert expected in res["error"]["message"]
    else:
        assert expected in res["status"]


@pytest.mark.parametrize(
    "home_id, room_id, mode, temp, json_fixture, expected",
    [
        ("91763b24c43d3e344f424e8b", "2746182631", "home", 14, "status_ok.json", "ok"),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            None,
            "status_ok.json",
            "ok",
        ),
    ],
)
def test_HomeData_setroomThermpoint(
    homeStatus,
    requests_mock,
    caplog,
    home_id,
    room_id,
    mode,
    temp,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._SETROOMTHERMPOINT_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        homeStatus.setroomThermpoint(
            home_id=home_id, room_id=room_id, mode=mode, temp=temp
        )["status"]
        == expected
    )


@pytest.mark.parametrize(
    "home_id, room_id, mode, temp, json_fixture, expected",
    [
        (
            None,
            None,
            None,
            None,
            "home_status_error_missing_home_id.json",
            "Missing home_id",
        ),
        (
            None,
            None,
            "home",
            None,
            "home_status_error_missing_home_id.json",
            "Missing home_id",
        ),
        (
            "91763b24c43d3e344f424e8b",
            None,
            "home",
            None,
            "home_status_error_missing_parameters.json",
            "Missing parameters",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            None,
            "home_status_error_missing_parameters.json",
            "Missing parameters",
        ),
    ],
)
def test_HomeData_setroomThermpoint_error(
    homeStatus,
    requests_mock,
    caplog,
    home_id,
    room_id,
    mode,
    temp,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._SETROOMTHERMPOINT_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        homeStatus.setroomThermpoint(
            home_id=home_id, room_id=room_id, mode=mode, temp=temp
        )["error"]["message"]
        == expected
    )


def test_HomeStatus_error_disconnected(auth, requests_mock):
    with open("fixtures/home_status_error_disconnected.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        pyatmo.HomeStatus(auth)
