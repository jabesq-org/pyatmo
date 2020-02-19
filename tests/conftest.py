"""Define shared fixtures."""
# pylint: disable=redefined-outer-name, protected-access
import json
from contextlib import contextmanager

import pytest

import pyatmo


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def auth(requests_mock):
    with open("fixtures/oauth2_token.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.auth.AUTH_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    authorization = pyatmo.ClientAuth(
        client_id="CLIENT_ID",
        client_secret="CLIENT_SECRET",
        username="USERNAME",
        password="PASSWORD",
        scope=" ".join(pyatmo.auth.ALL_SCOPES),
    )
    return authorization


@pytest.fixture(scope="function")
def home_data(auth, requests_mock):
    with open("fixtures/home_data_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.HomeData(auth)


@pytest.fixture(scope="function")
def home_status(auth, requests_mock):
    with open("fixtures/home_status_simple.json") as json_file:
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
    return pyatmo.HomeStatus(auth)


@pytest.fixture(scope="function")
def public_data(auth, requests_mock):
    with open("fixtures/public_data_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.public_data._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.PublicData(auth)


@pytest.fixture(scope="function")
def weather_station_data(auth, requests_mock):
    with open("fixtures/weatherstation_data_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.weather_station._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.WeatherStationData(auth)


@pytest.fixture(scope="function")
def home_coach_data(auth, requests_mock):
    with open("fixtures/home_coach_simple.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.home_coach._GETHOMECOACHDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.HomeCoachData(auth)


@pytest.fixture(scope="function")
def camera_home_data(auth, requests_mock):
    with open("fixtures/camera_home_data.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.camera._GETHOMEDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.CameraData(auth)
