"""Define tests for Camera module."""
# pylint: disable=protected-access
import datetime as dt
import json

import pytest
import time_machine

import pyatmo

from .conftest import does_not_raise


def test_camera_data(camera_home_data):
    assert camera_home_data.homes is not None


def test_home_data_no_body(auth, requests_mock):
    with open("fixtures/camera_data_empty.json", encoding="utf-8") as fixture_file:
        json_fixture = json.load(fixture_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMEDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        camera_data = pyatmo.CameraData(auth)
        camera_data.update()


def test_home_data_no_homes(auth, requests_mock):
    with open(
        "fixtures/camera_home_data_no_homes.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.load(fixture_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMEDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        camera_data = pyatmo.CameraData(auth)
        camera_data.update()


@pytest.mark.parametrize(
    "cid, expected",
    [
        ("12:34:56:00:f1:62", "Hall"),
        ("12:34:56:00:a5:a4", "Garden"),
        ("12:34:56:00:a5:a6", "NOC"),
        ("None", None),
        (None, None),
    ],
)
def test_camera_data_get_camera(camera_home_data, cid, expected):
    camera = camera_home_data.get_camera(cid)
    assert camera.get("name") == expected


def test_camera_data_get_module(camera_home_data):
    assert camera_home_data.get_module("00:00:00:00:00:00") is None


def test_camera_data_camera_urls(camera_home_data, requests_mock):
    cid = "12:34:56:00:f1:62"
    vpn_url = (
        "https://prodvpn-eu-2.netatmo.net/restricted/10.255.248.91/"
        "6d278460699e56180d47ab47169efb31/"
        "MpEylTU2MDYzNjRVD-LJxUnIndumKzLboeAwMDqTTg,,"
    )
    local_url = "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        f"{vpn_url}/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )

    with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        f"{local_url}/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )

    camera_home_data.update_camera_urls(cid)

    assert camera_home_data.camera_urls(cid) == (vpn_url, local_url)


def test_camera_data_update_camera_urls_empty(camera_home_data):
    camera_id = "12:34:56:00:f1:62"
    home_id = "91763b24c43d3e344f424e8b"
    camera_home_data.cameras[home_id][camera_id]["vpn_url"] = None
    camera_home_data.cameras[home_id][camera_id]["local_url"] = None

    camera_home_data.update_camera_urls(camera_id)

    assert camera_home_data.camera_urls(camera_id) == (None, None)


def test_camera_data_camera_urls_disconnected(auth, camera_ping, requests_mock):
    with open(
        "fixtures/camera_home_data_disconnected.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.load(fixture_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMEDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    camera_data = pyatmo.CameraData(auth)
    camera_data.update()
    cid = "12:34:56:00:f1:62"

    camera_data.update_camera_urls(cid)

    assert camera_data.camera_urls(cid) == (None, None)


@pytest.mark.parametrize(
    "home_id, expected",
    [("91763b24c43d3e344f424e8b", ["Richard Doe"])],
)
def test_camera_data_persons_at_home(camera_home_data, home_id, expected):
    assert camera_home_data.persons_at_home(home_id) == expected


@time_machine.travel(dt.datetime(2019, 6, 16))
@pytest.mark.parametrize(
    "name, cid, exclude, expected",
    [
        ("John Doe", "12:34:56:00:f1:62", None, True),
        ("Richard Doe", "12:34:56:00:f1:62", None, False),
        ("Unknown", "12:34:56:00:f1:62", None, False),
        ("John Doe", "12:34:56:00:f1:62", 1, False),
        ("John Doe", "12:34:56:00:f1:62", 50000, True),
        ("Jack Doe", "12:34:56:00:f1:62", None, False),
    ],
)
def test_camera_data_person_seen_by_camera(
    camera_home_data,
    name,
    cid,
    exclude,
    expected,
):
    assert (
        camera_home_data.person_seen_by_camera(name, cid, exclude=exclude) is expected
    )


def test_camera_data__known_persons(camera_home_data):
    known_persons = camera_home_data._known_persons("91763b24c43d3e344f424e8b")
    assert len(known_persons) == 3
    assert known_persons["91827374-7e04-5298-83ad-a0cb8372dff1"]["pseudo"] == "John Doe"


def test_camera_data_known_persons(camera_home_data):
    known_persons = camera_home_data.known_persons("91763b24c43d3e344f424e8b")
    assert len(known_persons) == 3
    assert known_persons["91827374-7e04-5298-83ad-a0cb8372dff1"] == "John Doe"


def test_camera_data_known_persons_names(camera_home_data):
    assert sorted(camera_home_data.known_persons_names("91763b24c43d3e344f424e8b")) == [
        "Jane Doe",
        "John Doe",
        "Richard Doe",
    ]


@time_machine.travel(dt.datetime(2019, 6, 16))
@pytest.mark.parametrize(
    "name, home_id, expected",
    [
        (
            "John Doe",
            "91763b24c43d3e344f424e8b",
            "91827374-7e04-5298-83ad-a0cb8372dff1",
        ),
        (
            "Richard Doe",
            "91763b24c43d3e344f424e8b",
            "91827376-7e04-5298-83af-a0cb8372dff3",
        ),
        ("Dexter Foe", "91763b24c43d3e344f424e8b", None),
    ],
)
def test_camera_data_get_person_id(camera_home_data, name, home_id, expected):
    assert camera_home_data.get_person_id(name, home_id) == expected


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
        (
            "91763b24c43d3e344f424e8b",
            None,
            "status_ok.json",
            "ok",
        ),
    ],
)
def test_camera_data_set_persons_away(
    camera_home_data,
    requests_mock,
    home_id,
    person_id,
    json_fixture,
    expected,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    mock_req = requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SETPERSONSAWAY_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert camera_home_data.set_persons_away(home_id, person_id)["status"] == expected
    if person_id is not None:
        assert (
            mock_req.request_history[0].text
            == f"home_id={home_id}&person_id={person_id}"
        )
    else:
        assert mock_req.request_history[0].text == f"home_id={home_id}"


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
        (
            "91763b24c43d3e344f424e8b",
            None,
            "status_ok.json",
            "ok",
        ),
    ],
)
def test_camera_data_set_persons_home(
    camera_home_data,
    requests_mock,
    home_id,
    person_ids,
    json_fixture,
    expected,
):
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    mock_req = requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SETPERSONSHOME_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert camera_home_data.set_persons_home(home_id, person_ids)["status"] == expected

    if isinstance(person_ids, list):
        assert (
            mock_req.request_history[0].text
            == f"home_id={home_id}&person_ids%5B%5D={'&person_ids%5B%5D='.join(person_ids)}"
        )
    elif person_ids:
        assert (
            mock_req.request_history[0].text
            == f"home_id={home_id}&person_ids%5B%5D={person_ids}"
        )
    else:
        assert mock_req.request_history[0].text == f"home_id={home_id}"


@time_machine.travel(dt.datetime(2019, 6, 16))
@pytest.mark.parametrize(
    "camera_id, exclude, expected, expectation",
    [
        ("12:34:56:00:f1:62", None, True, does_not_raise()),
        ("12:34:56:00:f1:62", 40000, True, does_not_raise()),
        ("12:34:56:00:f1:62", 5, False, does_not_raise()),
        (None, None, None, pytest.raises(pyatmo.NoDevice)),
    ],
)
def test_camera_data_someone_known_seen(
    camera_home_data,
    camera_id,
    exclude,
    expected,
    expectation,
):
    with expectation:
        assert camera_home_data.someone_known_seen(camera_id, exclude) == expected


@time_machine.travel(dt.datetime(2019, 6, 16))
@pytest.mark.parametrize(
    "camera_id, exclude, expected, expectation",
    [
        ("12:34:56:00:f1:62", None, False, does_not_raise()),
        ("12:34:56:00:f1:62", 40000, True, does_not_raise()),
        ("12:34:56:00:f1:62", 100, False, does_not_raise()),
        (None, None, None, pytest.raises(pyatmo.NoDevice)),
    ],
)
def test_camera_data_someone_unknown_seen(
    camera_home_data,
    camera_id,
    exclude,
    expected,
    expectation,
):
    with expectation:
        assert camera_home_data.someone_unknown_seen(camera_id, exclude) == expected


@time_machine.travel(dt.datetime(2019, 6, 16))
@pytest.mark.parametrize(
    "camera_id, exclude, expected, expectation",
    [
        ("12:34:56:00:f1:62", None, False, does_not_raise()),
        ("12:34:56:00:f1:62", 140000, True, does_not_raise()),
        ("12:34:56:00:f1:62", 130000, False, does_not_raise()),
        (None, None, False, pytest.raises(pyatmo.NoDevice)),
    ],
)
def test_camera_data_motion_detected(
    camera_home_data,
    camera_id,
    exclude,
    expected,
    expectation,
):
    with expectation:
        assert camera_home_data.motion_detected(camera_id, exclude) == expected


@pytest.mark.parametrize(
    "sid, expected",
    [
        ("12:34:56:00:8b:a2", "Hall"),
        ("12:34:56:00:8b:ac", "Kitchen"),
        ("None", None),
        (None, None),
    ],
)
def test_camera_data_get_smokedetector(camera_home_data, sid, expected):
    if smokedetector := camera_home_data.get_smokedetector(sid):
        assert smokedetector["name"] == expected
    else:
        assert smokedetector is expected


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
        (None, "12:34:56:00:f1:62", None, "on", "camera_set_state_ok.json", True),
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
    with open(f"fixtures/{json_fixture}", encoding="utf-8") as fixture_file:
        json_fixture = json.load(fixture_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.SETSTATE_ENDPOINT,
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


def test_camera_data_get_light_state(camera_home_data):
    camera_id = "12:34:56:00:a5:a4"
    expected = "auto"
    assert camera_home_data.get_light_state(camera_id) == expected


def test_camera_data_get_camera_picture(camera_home_data, requests_mock):
    image_id = "5c22739723720a6e278c43bf"
    key = "276751836a6d1a71447f8d975494c87bc125766a970f7e022e79e001e021d756"
    with open(
        "fixtures/camera_image_sample.jpg",
        "rb",
    ) as fixture_file:
        expect = fixture_file.read()

    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETCAMERAPICTURE_ENDPOINT,
        content=expect,
    )

    assert camera_home_data.get_camera_picture(image_id, key) == (expect, "jpeg")


def test_camera_data_get_profile_image(camera_home_data, requests_mock):
    with open(
        "fixtures/camera_image_sample.jpg",
        "rb",
    ) as fixture_file:
        expect = fixture_file.read()

    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETCAMERAPICTURE_ENDPOINT,
        content=expect,
    )
    assert camera_home_data.get_profile_image(
        "John Doe",
        "91763b24c43d3e344f424e8b",
    ) == (expect, "jpeg")
    assert camera_home_data.get_profile_image(
        "Jack Foe",
        "91763b24c43d3e344f424e8b",
    ) == (None, None)


@pytest.mark.parametrize(
    "home_id, event_id, device_type,  exception",
    [
        ("91763b24c43d3e344f424e8b", None, None, pytest.raises(pyatmo.ApiError)),
        (
            "91763b24c43d3e344f424e8b",
            "a1b2c3d4e5f6abcdef123456",
            None,
            does_not_raise(),
        ),
        ("91763b24c43d3e344f424e8b", None, "NOC", does_not_raise()),
        ("91763b24c43d3e344f424e8b", None, "NACamera", does_not_raise()),
        ("91763b24c43d3e344f424e8b", None, "NSD", does_not_raise()),
    ],
)
def test_camera_data_update_events(
    camera_home_data,
    requests_mock,
    home_id,
    event_id,
    device_type,
    exception,
):
    with open(
        "fixtures/camera_data_events_until.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.load(fixture_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETEVENTSUNTIL_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with exception:
        assert (
            camera_home_data.update_events(
                home_id=home_id,
                event_id=event_id,
                device_type=device_type,
            )
            is None
        )


def test_camera_data_outdoor_motion_detected(camera_home_data):
    camera_id = "12:34:56:00:a5:a4"
    assert camera_home_data.outdoor_motion_detected(camera_id) is False
    assert camera_home_data.outdoor_motion_detected(camera_id, 100) is False


def test_camera_data_human_detected(camera_home_data):
    camera_id = "12:34:56:00:a5:a4"
    assert camera_home_data.human_detected(camera_id) is False
    assert camera_home_data.human_detected(camera_id, 100) is False


def test_camera_data_animal_detected(camera_home_data):
    camera_id = "12:34:56:00:a5:a4"
    assert camera_home_data.animal_detected(camera_id) is False
    assert camera_home_data.animal_detected(camera_id, 100) is False


def test_camera_data_car_detected(camera_home_data):
    camera_id = "12:34:56:00:a5:a4"
    assert camera_home_data.car_detected(camera_id) is False
    assert camera_home_data.car_detected(camera_id, 100) is False


def test_camera_data_module_motion_detected(camera_home_data):
    camera_id = "12:34:56:00:f1:62"
    module_id = "12:34:56:00:f2:f1"
    assert camera_home_data.module_motion_detected(camera_id, module_id) is False
    assert camera_home_data.module_motion_detected(camera_id, module_id, 100) is False


def test_camera_data_module_opened(camera_home_data):
    camera_id = "12:34:56:00:f1:62"
    module_id = "12:34:56:00:f2:f1"
    assert camera_home_data.module_opened(camera_id, module_id) is False
    assert camera_home_data.module_opened(camera_id, module_id, 100) is False
