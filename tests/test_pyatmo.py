"""Define tests for authentication."""
import json

import pytest

import pyatmo


def test_ClientAuth(auth):
    assert auth.accessToken == (
        "91763b24c43d3e344f424e8b|880b55a08c758e87ff8755a00c6b8a12"
    )


def test_ClientAuth_invalid(requests_mock):
    with open("fixtures/invalid_grant.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo._AUTH_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        pyatmo.ClientAuth(
            clientId="CLIENT_ID",
            clientSecret="CLIENT_SECRET",
            username="USERNAME",
            password="PASSWORD",
        )
