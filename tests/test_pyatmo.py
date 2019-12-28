"""Define tests for untility methods."""
import json
import time

import pytest
import requests
import oauthlib

import pyatmo


def test_ClientAuth(auth):
    assert auth._oauth.token["access_token"] == (
        "91763b24c43d3e344f424e8b|880b55a08c758e87ff8755a00c6b8a12"
    )
    assert auth._oauth.token["refresh_token"] == (
        "91763b24c43d3e344f424e8b|87ff8755a00c6b8a120b55a08c758e93"
    )


def test_ClientAuth_invalid(requests_mock):
    with open("fixtures/invalid_grant.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.auth._AUTH_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(oauthlib.oauth2.rfc6749.errors.InvalidGrantError):
        pyatmo.ClientAuth(
            clientId="CLIENT_ID",
            clientSecret="CLIENT_SECRET",
            username="USERNAME",
            password="PASSWORD",
        )


def test_postRequest_json(auth, requests_mock):
    """Test wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        pyatmo.auth._BASE_URL,
        json={"a": "b"},
        headers={"content-type": "application/json"},
    )
    resp = auth.post_request(pyatmo.auth._BASE_URL, None)
    assert resp == {"a": "b"}


def test_postRequest_binary(auth, requests_mock):
    """Test wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        pyatmo.helpers._BASE_URL,
        text="Success",
        headers={"content-type": "application/text"},
    )
    resp = auth.post_request(pyatmo.helpers._BASE_URL, None)
    assert resp == b"Success"


@pytest.mark.parametrize("test_input,expected", [(200, None), (404, None)])
def test_postRequest_fail(auth, requests_mock, test_input, expected):
    """Test failing requests against the Netatmo API."""
    requests_mock.post(pyatmo.helpers._BASE_URL, status_code=test_input)
    if test_input == 200:
        resp = auth.post_request(pyatmo.helpers._BASE_URL, None)
        assert resp is expected
    else:
        with pytest.raises(pyatmo.ApiError):
            resp = auth.post_request(pyatmo.helpers._BASE_URL, None)


def test_postRequest_timeout(auth, requests_mock):
    """Test failing requests against the Netatmo API with timeouts."""
    requests_mock.post(pyatmo.helpers._BASE_URL, exc=requests.exceptions.ConnectTimeout)
    with pytest.raises(requests.exceptions.ConnectTimeout):
        assert auth.post_request(pyatmo.helpers._BASE_URL, None)


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (1, "1970-01-01_00:00:01"),
        (0, "1970-01-01_00:00:00"),
        (-1, "1969-12-31_23:59:59"),
        (2000000000, "2033-05-18_03:33:20"),
        ("1", "1970-01-01_00:00:01"),
        pytest.param("A", None, marks=pytest.mark.xfail),
        pytest.param([1], None, marks=pytest.mark.xfail),
        pytest.param({1}, None, marks=pytest.mark.xfail),
    ],
)
def test_toTimeString(test_input, expected):
    """Test time to string conversion."""
    assert pyatmo.helpers.toTimeString(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("1970-01-01_00:00:01", 1),
        ("1970-01-01_00:00:00", 0),
        ("1969-12-31_23:59:59", -1),
        ("2033-05-18_03:33:20", 2000000000),
    ],
)
def test_toEpoch(test_input, expected):
    """Test time to epoch conversion."""
    assert pyatmo.helpers.toEpoch(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("2018-06-21", (1529539200, 1529625600)),
        ("2000-01-01", (946684800, 946771200)),
        pytest.param("2000-04-31", None, marks=pytest.mark.xfail),
    ],
)
def test_todayStamps(monkeypatch, test_input, expected):
    """Test todayStamps function."""

    def mockreturn(format):
        return test_input

    monkeypatch.setattr(time, "strftime", mockreturn)
    assert pyatmo.helpers.todayStamps() == expected
