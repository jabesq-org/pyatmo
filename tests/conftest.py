"""Define shared fixtures."""
import json
from contextlib import contextmanager

import pytest

import pyatmo


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def auth(requests_mock):
    with open("fixtures/oauth2_token.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.auth._AUTH_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    authorization = pyatmo.ClientAuth(
        clientId="CLIENT_ID",
        clientSecret="CLIENT_SECRET",
        username="USERNAME",
        password="PASSWORD",
        scope="read_station read_camera access_camera "
        "read_thermostat write_thermostat "
        "read_presence access_presence read_homecoach",
    )
    return authorization


@pytest.fixture(scope="function")
def homeData(auth, requests_mock):
    with open("fixtures/home_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.HomeData(auth)


@pytest.fixture(scope="function")
def homeStatus(auth, requests_mock):
    with open("fixtures/home_status_simple.json") as f:
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
    return pyatmo.HomeStatus(auth)


@pytest.fixture(scope="function")
def publicData(auth, requests_mock):
    with open("fixtures/public_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.public_data._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.PublicData(auth)


@pytest.fixture(scope="function")
def weatherStationData(auth, requests_mock):
    with open("fixtures/weatherstation_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.weather_station._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.WeatherStationData(auth)


@pytest.fixture(scope="function")
def homeCoachData(auth, requests_mock):
    with open("fixtures/home_coach_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.home_coach._GETHOMECOACHDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.HomeCoachData(auth)


@pytest.fixture(scope="function")
def cameraHomeData(auth, requests_mock):
    with open("fixtures/camera_home_data.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.camera._GETHOMEDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.CameraData(auth)
