"""Define tests for Thermostat module."""
# pylint: disable=protected-access
import json

import pytest

import pyatmo
from tests.conftest import does_not_raise


def test_home_data(home_data):
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
    assert home_data.modules["91763b24c43d3e344f424e8b"] == expected


def test_home_data_no_data(auth, requests_mock):
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESDATA_ENDPOINT,
        json={},
        headers={"content-type": "application/json"},
    )
    home_data = pyatmo.HomeData(auth)
    with pytest.raises(pyatmo.NoDevice):
        home_data.update()


def test_home_data_no_body(auth, requests_mock):
    with open("fixtures/home_data_empty.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_data = pyatmo.HomeData(auth)
    with pytest.raises(pyatmo.NoDevice):
        home_data.update()


def test_home_data_no_homes(auth, requests_mock):
    with open("fixtures/home_data_no_homes.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_data = pyatmo.HomeData(auth)
    with pytest.raises(pyatmo.NoDevice):
        home_data.update()


def test_home_data_no_home_name(auth, requests_mock):
    with open("fixtures/home_data_nohomename.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_data = pyatmo.HomeData(auth)
    home_data.update()
    home_id = "91763b24c43d3e344f424e8b"
    assert home_data.homes[home_id]["name"] == "Unknown"


@pytest.mark.parametrize(
    "home_id, expected",
    [("91763b24c43d3e344f424e8b", "MYHOME"), ("91763b24c43d3e344f424e8c", "Unknown")],
)
def test_home_data_homes_by_id(home_data, home_id, expected):
    assert home_data.homes[home_id]["name"] == expected


def test_home_data_get_selected_schedule(home_data):
    assert (
        home_data._get_selected_schedule("91763b24c43d3e344f424e8b")["name"]
        == "Default"
    )
    assert home_data._get_selected_schedule("Unknown") == {}


@pytest.mark.parametrize(
    "t_home_id, t_sched_id, expected",
    [
        ("91763b24c43d3e344f424e8b", "591b54a2764ff4d50d8b5795", does_not_raise()),
        (
            "91763b24c43d3e344f424e8b",
            "123456789abcdefg12345678",
            pytest.raises(pyatmo.NoSchedule),
        ),
    ],
)
def test_home_data_switch_home_schedule(
    home_data,
    requests_mock,
    t_home_id,
    t_sched_id,
    expected,
):
    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SWITCHHOMESCHEDULE_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with expected:
        home_data.switch_home_schedule(home_id=t_home_id, schedule_id=t_sched_id)


@pytest.mark.parametrize(
    "home_id, expected",
    [("91763b24c43d3e344f424e8b", 14), ("00000000000000000000000", None)],
)
def test_home_data_get_away_temp(home_data, home_id, expected):
    assert home_data.get_away_temp(home_id) == expected


@pytest.mark.parametrize(
    "home_id, expected",
    [("91763b24c43d3e344f424e8b", 7), ("00000000000000000000000", None)],
)
def test_home_data_get_hg_temp(home_data, home_id, expected):
    assert home_data.get_hg_temp(home_id) == expected


@pytest.mark.parametrize(
    "home_id, module_id, expected",
    [
        ("91763b24c43d3e344f424e8b", "2746182631", "NATherm1"),
        ("91763b24c43d3e344f424e8b", "2833524037", "NRV"),
        ("91763b24c43d3e344f424e8b", "0000000000", None),
    ],
)
def test_home_data_thermostat_type(home_data, home_id, module_id, expected):
    assert home_data.get_thermostat_type(home_id, module_id) == expected


@pytest.mark.parametrize(
    "home_id, room_id, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            "2746182631",
            {
                "id": "2746182631",
                "reachable": True,
                "therm_measured_temperature": 19.8,
                "therm_setpoint_temperature": 12,
                "therm_setpoint_mode": "away",
                "therm_setpoint_start_time": 1559229567,
                "therm_setpoint_end_time": 0,
            },
        ),
    ],
)
def test_home_status(home_status, room_id, expected):
    assert len(home_status.rooms) == 3
    assert home_status.rooms[room_id] == expected


def test_home_status_error_and_data(auth, requests_mock):
    with open(
        "fixtures/home_status_error_and_data.json",
        encoding="utf-8",
    ) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESTATUS_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_status = pyatmo.HomeStatus(auth, home_id="91763b24c43d3e344f424e8b")
    home_status.update()
    assert len(home_status.rooms) == 3

    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert home_status.rooms["2746182631"] == expexted


def test_home_status_error(auth, requests_mock):
    with open("fixtures/home_status_empty.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESTATUS_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        home_status = pyatmo.HomeStatus(auth, home_id="91763b24c43d3e344f424e8b")
        home_status.update()


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_get_room(home_status):
    expexted = {
        "id": "2746182631",
        "reachable": True,
        "therm_measured_temperature": 19.8,
        "therm_setpoint_temperature": 12,
        "therm_setpoint_mode": "away",
        "therm_setpoint_start_time": 1559229567,
        "therm_setpoint_end_time": 0,
    }
    assert home_status.get_room("2746182631") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.get_room("0000000000")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_get_thermostat(home_status):
    expexted = {
        "id": "12:34:56:00:01:ae",
        "reachable": True,
        "type": "NATherm1",
        "firmware_revision": 65,
        "rf_strength": 58,
        "battery_level": 3780,
        "boiler_valve_comfort_boost": False,
        "boiler_status": True,
        "anticipating": False,
        "bridge": "12:34:56:00:fa:d0",
        "battery_state": "high",
    }
    assert home_status.get_thermostat("12:34:56:00:01:ae") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.get_thermostat("00:00:00:00:00:00")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_get_relay(home_status):
    expexted = {
        "id": "12:34:56:00:fa:d0",
        "type": "NAPlug",
        "firmware_revision": 174,
        "rf_strength": 107,
        "wifi_strength": 42,
    }
    assert home_status.get_relay("12:34:56:00:fa:d0") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.get_relay("00:00:00:00:00:00")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_get_valve(home_status):
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
    assert home_status.get_valve("12:34:56:03:a5:54") == expexted
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.get_valve("00:00:00:00:00:00")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_set_point(home_status):
    assert home_status.set_point("2746182631") == 12
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.set_point("0000000000")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_set_point_mode(home_status):
    assert home_status.set_point_mode("2746182631") == "away"
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.set_point_mode("0000000000")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_measured_temperature(home_status):
    assert home_status.measured_temperature("2746182631") == 19.8
    with pytest.raises(pyatmo.InvalidRoom):
        assert home_status.measured_temperature("0000000000")


@pytest.mark.parametrize("home_id", ["91763b24c43d3e344f424e8b"])
def test_home_status_boiler_status(home_status):
    assert home_status.boiler_status("12:34:56:00:01:ae") is True


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
def test_home_status_set_thermmode(
    home_status,
    requests_mock,
    mode,
    end_time,
    schedule_id,
    json_fixture,
    expected,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SETTHERMMODE_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    res = home_status.set_thermmode(
        mode=mode,
        end_time=end_time,
        schedule_id=schedule_id,
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
def test_home_status_set_room_thermpoint(
    home_status,
    requests_mock,
    room_id,
    mode,
    temp,
    end_time,
    json_fixture,
    expected,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SETROOMTHERMPOINT_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        home_status.set_room_thermpoint(
            room_id=room_id,
            mode=mode,
            temp=temp,
            end_time=end_time,
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
def test_home_status_set_room_thermpoint_error(
    home_status,
    requests_mock,
    room_id,
    mode,
    temp,
    json_fixture,
    expected,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SETROOMTHERMPOINT_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        home_status.set_room_thermpoint(room_id=room_id, mode=mode, temp=temp)["error"][
            "message"
        ]
        == expected
    )


def test_home_status_error_disconnected(
    auth,
    requests_mock,
    home_id="91763b24c43d3e344f424e8b",
):
    with open(
        "fixtures/home_status_error_disconnected.json",
        encoding="utf-8",
    ) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESTATUS_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.GETHOMESDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        home_status = pyatmo.HomeStatus(auth, home_id)
        home_status.update()
