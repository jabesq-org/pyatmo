"""Define tests for authentication."""
import json
import pytest
import pyatmo


def test_postRequest(requests_mock):
    """Test the wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        pyatmo._BASE_URL, json={"a": "b"}, headers={"content-type": "application/json"}
    )
    resp = pyatmo.postRequest(pyatmo._BASE_URL, None)
    assert resp == {"a": "b"}

    requests_mock.post(
        pyatmo._BASE_URL, text="Success", headers={"content-type": "application/text"}
    )
    resp = pyatmo.postRequest(pyatmo._BASE_URL, None)
    assert resp == b"Success"


def test_ClientAuth(requests_mock):
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
    assert (
        authorization.accessToken
        == "91763b24c43d3e344f424e8b|880b55a08c758e87ff8755a00c6b8a12"
    )


@pytest.mark.xfail(raises=KeyError)
def test_ClientAuth_invalid(requests_mock):
    with open("fixtures/invalid_grant.json") as f:
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
    )
