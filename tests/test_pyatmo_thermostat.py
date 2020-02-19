"""Define tests for Thermostat module."""
# pylint: disable=protected-access
import json

import pytest

import pyatmo

from tests.conftest import does_not_raise


def test_home_data(home_data):
    assert home_data.default_home == "MYHOME"
    assert home_data.default_home_id == "91763b24c43d3e344f424e8b"
    assert len(home_data.rooms[home_data.default_home_id]) == 4

    assert len(home_data.modules[home_data.default_home_id]) == 5

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
    assert home_data.modules[home_data.default_home_id] == expected


def test_home_data_no_data(auth, requests_mock):
    requests_mock.post(pyatmo.thermostat._GETHOMESDATA_REQ, text="None")
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.HomeData(auth)


def test_home_data_no_body(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.HomeData(auth)


def test_home_data_no_home_name(auth, requests_mock):
    with open("fixtures/home_data_nohomename.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_data = pyatmo.HomeData(auth)
    home_id = "91763b24c43d3e344f424e8b"
    assert home_data.home_by_id(home_id)["name"] == "Unknown"


def test_home_data_home_by_id(home_data):
    home_id = "91763b24c43d3e344f424e8b"
    assert home_data.home_by_id(home_id)["name"] == "MYHOME"
    home_id = "91763b24c43d3e344f424e8c"
    assert home_data.home_by_id(home_id)["name"] == "Unknown"


def test_home_data_home_by_name(home_data):
    assert home_data.home_by_name()["name"] == "MYHOME"
    assert home_data.home_by_name()["id"] == "91763b24c43d3e344f424e8b"


def test_home_data_get_home_id(home_data):
    assert home_data.get_home_id() == "91763b24c43d3e344f424e8b"
    assert home_data.get_home_id("MYHOME") == "91763b24c43d3e344f424e8b"
    with pytest.raises(pyatmo.InvalidHome):
        assert home_data.get_home_id("InvalidName")


def test_home_data_get_home_name(home_data):
    assert home_data.get_home_name() == "MYHOME"
    home_id = "91763b24c43d3e344f424e8b"
    assert home_data.get_home_name(home_id) == "MYHOME"
    home_id = "91763b24c43d3e344f424e8c"
    assert home_data.get_home_name(home_id) == "Unknown"


def test_home_data_get_selected_schedule(home_data):
    assert home_data.get_selected_schedule()["name"] == "Default"
    assert home_data.get_selected_schedule("MYHOME")["name"] == "Default"
    with pytest.raises(pyatmo.InvalidHome):
        assert home_data.get_selected_schedule("Unknown")


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
def test_home_data_switch_home_schedule(
    home_data, requests_mock, t_home, t_sched_id, t_sched, expected
):
    with open("fixtures/status_ok.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._SWITCHHOMESCHEDULE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with expected:
        home_data.switch_home_schedule(
            schedule_id=t_sched_id, schedule=t_sched, home=t_home
        )


def test_home_status(home_status):
    assert len(home_status.rooms) == 3
    assert home_status.default_room["id"] == "2746182631"

    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert home_status.default_room == expexted


def test_home_status_error_and_data(auth, requests_mock):
    with open("fixtures/home_status_error_and_data.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_status = pyatmo.HomeStatus(auth)
    assert len(home_status.rooms) == 3
    assert home_status.default_room["id"] == "2746182631"

    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert home_status.default_room == expexted


def test_home_status_error(auth, requests_mock):
    with open("fixtures/home_status_empty.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.HomeStatus(auth)


def test_home_status_room_by_id(home_status):
    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert home_status.room_by_id("2746182631") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.room_by_id("0000000000")


def test_home_status_thermostat_by_id(home_status):
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
    assert home_status.thermostat_by_id("12:34:56:00:01:ae") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.thermostat_by_id("00:00:00:00:00:00")


def test_home_status_relay_by_id(home_status):
    expexted = {
        "id": "12:34:56:00:fa:d0",
        "type": "NAPlug",
        "firmware_revision": 174,
        "rf_strength": 107,
        "wifi_strength": 42,
    }
    assert home_status.relay_by_id("12:34:56:00:fa:d0") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.relay_by_id("00:00:00:00:00:00")


def test_home_status_valve_by_id(home_status):
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
    assert home_status.valve_by_id("12:34:56:03:a5:54") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.valve_by_id("00:00:00:00:00:00")


def test_home_status_set_point(home_status):
    assert home_status.set_point() == 12
    assert home_status.set_point("2746182631") == 12
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.set_point("0000000000")


def test_home_status_set_point_mode(home_status):
    assert home_status.set_point_mode() == "away"
    assert home_status.set_point_mode("2746182631") == "away"
    assert home_status.set_point_mode("0000000000") is None


def test_home_status_get_away_temp(home_status):
    assert home_status.get_away_temp() == 14
    assert home_status.get_away_temp("MYHOME") == 14
    assert home_status.get_away_temp("InvalidName") is None
    assert home_status.get_away_temp(home_id="91763b24c43d3e344f424e8b") == 14
    assert home_status.get_away_temp(home_id="00000000000000000000000") is None


def test_home_status_get_hg_temp(home_status):
    assert home_status.get_hg_temp() == 7
    assert home_status.get_hg_temp("MYHOME") == 7
    with pytest.raises(pyatmo.InvalidHome):
        assert home_status.get_hg_temp("InvalidHome")
    assert home_status.get_hg_temp(home_id="91763b24c43d3e344f424e8b") == 7
    assert home_status.get_hg_temp(home_id="00000000000000000000000") is None


def test_home_status_measured_temperature(home_status):
    assert home_status.measured_temperature() == 19.8
    assert home_status.measured_temperature("2746182631") == 19.8
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.measured_temperature("0000000000")


def test_home_status_boiler_status(home_status):
    assert home_status.boiler_status() is False


def test_home_status_thermostat_type(home_status):
    assert home_status.thermostat_type("MYHOME", "2746182631") == "NATherm1"
    assert home_status.thermostat_type("MYHOME", "2833524037") == "NRV"
    with pytest.raises(pyatmo.InvalidHome):
        assert home_status.thermostat_type("InvalidHome", "2833524037")
    assert home_status.thermostat_type("MYHOME", "0000000000") is None


@pytest.mark.parametrize(
    "home_id, mode, end_time, schedule_id, json_fixture, expected",
    [
        (
            None,
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
        ),
        (
            "91763b24c43d3e344f424e8b",
            None,
            None,
            None,
            "home_status_error_mode_is_missing.json",
            "mode is missing",
        ),
        (
            "invalidID",
            "away",
            None,
            None,
            "home_status_error_invalid_id.json",
            "Invalid id",
        ),
        ("91763b24c43d3e344f424e8b", "away", None, None, "status_ok.json", "ok"),
        ("91763b24c43d3e344f424e8b", "away", 1559162650, None, "status_ok.json", "ok"),
        (
            "91763b24c43d3e344f424e8b",
            "away",
            1559162650,
            0000000,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "schedule",
            None,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "schedule",
            1559162650,
            "591b54a2764ff4d50d8b5795",
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "schedule",
            None,
            "blahblahblah",
            "home_status_error_invalid_schedule_id.json",
            "schedule <blahblahblah> is not therm schedule",
        ),
    ],
)
def test_home_data_set_therm_mode(
    home_status,
    requests_mock,
    caplog,
    home_id,
    mode,
    end_time,
    schedule_id,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._SETTHERMMODE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    res = home_status.set_therm_mode(
        home_id=home_id, mode=mode, end_time=end_time, schedule_id=schedule_id
    )
    if "error" in res:
        assert expected in res["error"]["message"]
    else:
        assert expected in res["status"]


@pytest.mark.parametrize(
    "home_id, room_id, mode, temp, end_time, json_fixture, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            14,
            None,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            14,
            1559162650,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            None,
            None,
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            "home",
            None,
            1559162650,
            "status_ok.json",
            "ok",
        ),
    ],
)
def test_home_data_set_room_therm_point(
    home_status,
    requests_mock,
    caplog,
    home_id,
    room_id,
    mode,
    temp,
    end_time,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._SETROOMTHERMPOINT_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        home_status.set_room_therm_point(
            home_id=home_id, room_id=room_id, mode=mode, temp=temp, end_time=end_time
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
def test_home_data_set_room_therm_point_error(
    home_status, requests_mock, home_id, room_id, mode, temp, json_fixture, expected
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._SETROOMTHERMPOINT_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        home_status.set_room_therm_point(
            home_id=home_id, room_id=room_id, mode=mode, temp=temp
        )["error"]["message"]
        == expected
    )


def test_home_status_error_disconnected(auth, requests_mock):
    with open("fixtures/home_status_error_disconnected.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        pyatmo.HomeStatus(auth)
