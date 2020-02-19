"""Define tests for Camera module."""
# pylint: disable=protected-access
import json

import pytest
from freezegun import freeze_time

import pyatmo

INVALID_NAME = "InvalidName"


def test_camera_data(camera_home_data):
    assert camera_home_data.default_home == "MYHOME"
    assert camera_home_data.default_camera["id"] == "12:34:56:00:f1:62"
    assert camera_home_data.default_camera["name"] == "Hall"


@pytest.mark.parametrize(
    "hid, expected",
    [
        ("91763b24c43d3e344f424e8b", "MYHOME"),
        (INVALID_NAME, "MYHOME"),
        pytest.param(None, None),
    ],
)
def test_camera_data_home_by_id(camera_home_data, hid, expected):
    if hid is None or hid == INVALID_NAME:
        assert camera_home_data.home_by_id(hid) is None
    else:
        assert camera_home_data.home_by_id(hid)["name"] == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("MYHOME", "91763b24c43d3e344f424e8b"),
        (None, "91763b24c43d3e344f424e8b"),
        ("", "91763b24c43d3e344f424e8b"),
        pytest.param(INVALID_NAME, None),
    ],
)
def test_camera_data_home_by_name(camera_home_data, name, expected):
    if name == INVALID_NAME:
        with pytest.raises(pyatmo.exceptions.InvalidHome):
            assert camera_home_data.home_by_name(name)
    else:
        assert camera_home_data.home_by_name(name)["id"] == expected


@pytest.mark.parametrize(
    "cid, expected",
    [
        ("12:34:56:00:f1:62", "Hall"),
        ("12:34:56:00:a5:a4", "Garden"),
        ("None", None),
        (None, None),
    ],
)
def test_camera_data_camera_by_id(camera_home_data, cid, expected):
    camera = camera_home_data.camera_by_id(cid)
    if camera:
        assert camera["name"] == expected
    else:
        assert camera is expected


@pytest.mark.parametrize(
    "name, home, home_id, expected",
    [
        ("Hall", None, None, "12:34:56:00:f1:62"),
        (None, None, None, "12:34:56:00:f1:62"),
        ("", None, None, "12:34:56:00:f1:62"),
        ("Hall", "MYHOME", None, "12:34:56:00:f1:62"),
        ("Hall", None, "91763b24c43d3e344f424e8b", "12:34:56:00:f1:62"),
        (None, None, "91763b24c43d3e344f424e8b", "12:34:56:00:f1:62"),
        (None, "MYHOME", None, "12:34:56:00:f1:62"),
        ("", "MYHOME", None, "12:34:56:00:f1:62"),
        ("Garden", "MYHOME", None, "12:34:56:00:a5:a4"),
        ("Garden", None, "InvalidHomeID", "12:34:56:00:a5:a4"),
        (INVALID_NAME, None, None, None),
        (None, INVALID_NAME, None, None),
    ],
)
def test_camera_data_camera_by_name(camera_home_data, name, home, home_id, expected):
    if home == INVALID_NAME or name == INVALID_NAME or home_id == "InvalidHomeID":
        assert camera_home_data.camera_by_name(name, home, home_id) is None
    elif home_id is None:
        assert camera_home_data.camera_by_name(name, home)["id"] == expected
    elif home is None:
        assert camera_home_data.camera_by_name(name, home_id=home_id)["id"] == expected
    else:
        assert camera_home_data.camera_by_name(name, home, home_id)["id"] == expected


def test_camera_data_module_by_id(camera_home_data):
    assert camera_home_data.module_by_id("00:00:00:00:00:00") is None


def test_camera_data_module_by_name(camera_home_data):
    assert camera_home_data.module_by_name() is None


@pytest.mark.parametrize(
    "camera, home, cid, expected",
    [
        (None, None, None, "NACamera"),
        ("Hall", None, None, "NACamera"),
        ("Hall", "MYHOME", None, "NACamera"),
        (None, "MYHOME", None, "NACamera"),
        (None, "MYHOME", "12:34:56:00:f1:62", "NACamera"),
        (None, None, "12:34:56:00:f1:62", "NACamera"),
        ("Garden", None, None, "NOC"),
        (INVALID_NAME, None, None, None),
        pytest.param(None, INVALID_NAME, None, None),
    ],
)
def test_camera_data_camera_type(camera_home_data, camera, home, cid, expected):
    assert camera_home_data.camera_type(camera, home, cid) == expected


def test_camera_data_camera_urls(camera_home_data, requests_mock):
    vpn_url = (
        "https://prodvpn-eu-2.netatmo.net/restricted/10.255.248.91/"
        "6d278460699e56180d47ab47169efb31/"
        "MpEylTU2MDYzNjRVD-LJxUnIndumKzLboeAwMDqTTg,,"
    )
    local_url = "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    with open("fixtures/camera_ping.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        vpn_url + "/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/camera_ping.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        local_url + "/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )

    camera_id = "12:34:56:00:f1:62"
    assert camera_home_data.camera_urls(camera_id) == (vpn_url, local_url)


def test_camera_data_camera_urls_disconnected(auth, requests_mock):
    with open("fixtures/camera_home_data_disconnected.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.camera._GETHOMEDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    camera_data = pyatmo.CameraData(auth)
    camera_id = "12:34:56:00:f1:62"
    assert camera_data.camera_urls(camera_id) == (None, None)


@pytest.mark.parametrize(
    "home, expected",
    [
        (None, ["Richard Doe"]),
        ("MYHOME", ["Richard Doe"]),
        pytest.param(
            INVALID_NAME,
            None,
            # marks=pytest.mark.xfail(reason="Invalid home name not handled yet"),
        ),
    ],
)
def test_camera_data_persons_at_home(camera_home_data, home, expected):
    if home == INVALID_NAME:
        with pytest.raises(pyatmo.exceptions.InvalidHome):
            assert camera_home_data.persons_at_home_by_name(home)
    else:
        assert camera_home_data.persons_at_home_by_name(home) == expected


@freeze_time("2019-06-16")
@pytest.mark.parametrize(
    "name, exclude, expected",
    [
        ("John Doe", None, True),
        ("Richard Doe", None, False),
        ("Unknown", None, False),
        ("John Doe", 1, False),
        ("John Doe", 50000, True),
        ("Jack Doe", None, False),
    ],
)
def test_camera_data_person_seen_by_camera(camera_home_data, name, exclude, expected):
    camera_id = "12:34:56:00:f1:62"
    assert (
        camera_home_data.person_seen_by_camera(name, camera_id, exclude=exclude)
        is expected
    )


def test_camera_data__known_persons_dict(camera_home_data):
    known_persons = camera_home_data._known_persons_dict()
    assert len(known_persons) == 3
    assert known_persons["91827374-7e04-5298-83ad-a0cb8372dff1"]["pseudo"] == "John Doe"


def test_camera_data_known_persons_names(camera_home_data):
    assert set(camera_home_data.known_persons_names()) == {
        "Jane Doe",
        "John Doe",
        "Richard Doe",
    }


@freeze_time("2019-06-16")
@pytest.mark.parametrize(
    "name, expected",
    [
        ("John Doe", "91827374-7e04-5298-83ad-a0cb8372dff1"),
        ("Richard Doe", "91827376-7e04-5298-83af-a0cb8372dff3"),
    ],
)
def test_camera_data_get_person_id(camera_home_data, name, expected):
    assert camera_home_data.get_person_id(name) == expected


@pytest.mark.parametrize(
    "home_id, person_id, json_fixture, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            "91827374-7e04-5298-83ad-a0cb8372dff1",
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "91827376-7e04-5298-83af-a0cb8372dff3",
            "status_ok.json",
            "ok",
        ),
    ],
)
def test_camera_data_set_person_away(
    camera_home_data, requests_mock, home_id, person_id, json_fixture, expected
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.camera._SETPERSONSAWAY_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert camera_home_data.set_person_away(person_id, home_id)["status"] == expected


@pytest.mark.parametrize(
    "home_id, person_ids, json_fixture, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            [
                "91827374-7e04-5298-83ad-a0cb8372dff1",
                "91827376-7e04-5298-83af-a0cb8372dff3",
            ],
            "status_ok.json",
            "ok",
        ),
        (
            "91763b24c43d3e344f424e8b",
            "91827376-7e04-5298-83af-a0cb8372dff3",
            "status_ok.json",
            "ok",
        ),
    ],
)
def test_camera_data_set_persons_home(
    camera_home_data, requests_mock, home_id, person_ids, json_fixture, expected
):
    with open("fixtures/%s" % json_fixture) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.camera._SETPERSONSHOME_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert camera_home_data.set_persons_home(person_ids, home_id)["status"] == expected


@freeze_time("2019-06-16")
@pytest.mark.parametrize(
    "camera_id, exclude, expected",
    [("12:34:56:00:f1:62", None, True), ("12:34:56:00:f1:62", 5, False)],
)
def test_camera_data_someone_known_seen(camera_home_data, camera_id, exclude, expected):
    assert camera_home_data.someone_known_seen(camera_id, exclude) == expected


@freeze_time("2019-06-16")
@pytest.mark.parametrize(
    "camera_id, exclude, expected",
    [("12:34:56:00:f1:62", None, False), ("12:34:56:00:f1:62", 100, False)],
)
def test_camera_data_someone_unknown_seen(
    camera_home_data, camera_id, exclude, expected
):
    assert camera_home_data.someone_unknown_seen(camera_id, exclude) == expected


@freeze_time("2019-06-16")
@pytest.mark.parametrize(
    "camera_id, exclude, expected",
    [
        ("12:34:56:00:f1:62", None, False),
        ("12:34:56:00:f1:62", 140000, True),
        ("12:34:56:00:f1:62", 130000, False),
    ],
)
def test_camera_data_motion_detected(camera_home_data, camera_id, exclude, expected):
    assert camera_home_data.motion_detected(camera_id, exclude) == expected


def test_camera_data_get_home_name(camera_home_data):
    assert camera_home_data.get_home_name() == "MYHOME"
    home_id = "91763b24c43d3e344f424e8b"
    assert camera_home_data.get_home_name(home_id) == "MYHOME"
    home_id = "91763b24c43d3e344f424e8c"
    assert camera_home_data.get_home_name(home_id) == "Unknown"
    home_id = "InvalidHomeID"
    with pytest.raises(pyatmo.InvalidHome):
        assert camera_home_data.get_home_name(home_id) == "Unknown"


def test_camera_data_get_home_id(camera_home_data):
    assert camera_home_data.get_home_id() == "91763b24c43d3e344f424e8b"
    assert camera_home_data.get_home_id("MYHOME") == "91763b24c43d3e344f424e8b"
    with pytest.raises(pyatmo.InvalidHome):
        assert camera_home_data.get_home_id("InvalidName")


@pytest.mark.parametrize(
    "sid, expected",
    [
        ("12:34:56:00:8b:a2", "Hall"),
        ("12:34:56:00:8b:ac", "Kitchen"),
        ("None", None),
        (None, None),
    ],
)
def test_camera_data_smokedetector_by_id(camera_home_data, sid, expected):
    smokedetector = camera_home_data.smokedetector_by_id(sid)
    if smokedetector:
        assert smokedetector["name"] == expected
    else:
        assert smokedetector is expected


@pytest.mark.parametrize(
    "name, home, home_id, expected",
    [
        ("Hall", None, None, "12:34:56:00:8b:a2"),
        (None, None, None, None),
        ("", None, None, "12:34:56:00:8b:a2"),
        ("Hall", "MYHOME", None, "12:34:56:00:8b:a2"),
        ("Hall", None, "91763b24c43d3e344f424e8b", "12:34:56:00:8b:a2"),
        (None, None, "91763b24c43d3e344f424e8b", "12:34:56:00:8b:a2"),
        (None, "MYHOME", None, "12:34:56:00:8b:a2"),
        ("", "MYHOME", None, "12:34:56:00:8b:a2"),
        ("Kitchen", "MYHOME", None, "12:34:56:00:8b:ac"),
        (INVALID_NAME, None, None, None),
        (None, INVALID_NAME, None, None),
    ],
)
def test_camera_data_smokedetector_by_name(
    camera_home_data, name, home, home_id, expected
):
    if (
        home == INVALID_NAME
        or name == INVALID_NAME
        or (name is None and home is None and home_id is None)
    ):
        assert camera_home_data.smokedetector_by_name(name, home, home_id) is None
    elif home_id is None:
        assert camera_home_data.smokedetector_by_name(name, home)["id"] == expected
    elif home is None:
        assert (
            camera_home_data.smokedetector_by_name(name, home_id=home_id)["id"]
            == expected
        )
    else:
        assert (
            camera_home_data.smokedetector_by_name(name, home, home_id)["id"]
            == expected
        )


@pytest.mark.parametrize(
    "home_id, camera_id, floodlight, monitoring, json_fixture, expected",
    [
        (
            "91763b24c43d3e344f424e8b",
            "12:34:56:00:f1:ff",
            "on",
            None,
            "camera_set_state_error.json",
            False,
        ),
        (
            "91763b24c43d3e344f424e8b",
            "12:34:56:00:f1:62",
            None,
            "on",
            "camera_set_state_ok.json",
            True,
        ),
        (None, "12:34:56:00:f1:62", None, "on", "camera_set_state_ok.json", True,),
        (
            "91763b24c43d3e344f424e8b",
            "12:34:56:00:f1:62",
            "auto",
            "on",
            "camera_set_state_ok.json",
            True,
        ),
        (
            "91763b24c43d3e344f424e8b",
            "12:34:56:00:f1:62",
            None,
            "on",
            "camera_set_state_error_already_on.json",
            True,
        ),
        (
            "91763b24c43d3e344f424e8b",
            "12:34:56:00:f1:62",
            "on",
            None,
            "camera_set_state_error_wrong_parameter.json",
            False,
        ),
    ],
)
def test_camera_data_set_state(
    camera_home_data,
    requests_mock,
    home_id,
    camera_id,
    floodlight,
    monitoring,
    json_fixture,
    expected,
):
    with open("fixtures/%s" % json_fixture) as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.camera._SETSTATE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        camera_home_data.set_state(
            home_id=home_id,
            camera_id=camera_id,
            floodlight=floodlight,
            monitoring=monitoring,
        )
        == expected
    )
