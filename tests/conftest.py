"""Define shared fixtures."""
import json
import pytest
import pyatmo


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
