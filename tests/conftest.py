"""Define shared fixtures."""
import json

import pytest

import pyatmo
import smart_home.Thermostat
import smart_home.PublicData


@pytest.fixture(scope="function")
def auth(requests_mock):
    with open("fixtures/oauth2_token.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo._AUTH_REQ,
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
        smart_home.Thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.HomeData(auth)


@pytest.fixture(scope="function")
def homeStatus(auth, requests_mock):
    with open("fixtures/home_status_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.Thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with open("fixtures/home_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.Thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.HomeStatus(auth)


@pytest.fixture(scope="function")
def thermostatData(auth, requests_mock):
    with open("fixtures/thermostat_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.Thermostat._GETTHERMOSTATDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.ThermostatData(auth)


@pytest.fixture(scope="function")
def publicData(auth, requests_mock):
    with open("fixtures/public_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.PublicData._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.PublicData(auth)
