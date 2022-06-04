"""Define tests for untility methods."""
# pylint: disable=protected-access
import json
import time

import oauthlib
import pytest

import pyatmo


def test_client_auth(auth):
    assert auth._oauth.token["access_token"] == (
        "91763b24c43d3e344f424e8b|880b55a08c758e87ff8755a00c6b8a12"
    )
    assert auth._oauth.token["refresh_token"] == (
        "91763b24c43d3e344f424e8b|87ff8755a00c6b8a120b55a08c758e93"
    )


def test_client_auth_invalid(requests_mock):
    with open("fixtures/invalid_grant.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.auth.AUTH_REQ_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(oauthlib.oauth2.rfc6749.errors.InvalidGrantError):
        pyatmo.ClientAuth(
            client_id="CLIENT_ID",
            client_secret="CLIENT_SECRET",
            username="USERNAME",
            password="PASSWORD",
        )


def test_post_request_json(auth, requests_mock):
    """Test wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL,
        json={"a": "b"},
        headers={"content-type": "application/json"},
    )
    resp = auth.post_request(pyatmo.const.DEFAULT_BASE_URL, None).json()
    assert resp == {"a": "b"}


def test_post_request_binary(auth, requests_mock):
    """Test wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL,
        text="Success",
        headers={"content-type": "application/text"},
    )
    resp = auth.post_request(pyatmo.const.DEFAULT_BASE_URL, None).content
    assert resp == b"Success"


@pytest.mark.parametrize("test_input,expected", [(200, None), (404, None), (401, None)])
def test_post_request_fail(auth, requests_mock, test_input, expected):
    """Test failing requests against the Netatmo API."""
    requests_mock.post(pyatmo.const.DEFAULT_BASE_URL, status_code=test_input)

    if test_input == 200:
        resp = auth.post_request(pyatmo.const.DEFAULT_BASE_URL, None).content
        assert resp is expected
    else:
        with pytest.raises(pyatmo.ApiError):
            resp = auth.post_request(pyatmo.const.DEFAULT_BASE_URL, None).content


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
def test_to_time_string(test_input, expected):
    """Test time to string conversion."""
    assert pyatmo.helpers.to_time_string(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("1970-01-01_00:00:01", 1),
        ("1970-01-01_00:00:00", 0),
        ("1969-12-31_23:59:59", -1),
        ("2033-05-18_03:33:20", 2000000000),
    ],
)
def test_to_epoch(test_input, expected):
    """Test time to epoch conversion."""
    assert pyatmo.helpers.to_epoch(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("2018-06-21", (1529539200, 1529625600)),
        ("2000-01-01", (946684800, 946771200)),
        pytest.param("2000-04-31", None, marks=pytest.mark.xfail),
    ],
)
def test_today_stamps(monkeypatch, test_input, expected):
    """Test today_stamps function."""

    def mockreturn(_):
        return test_input

    monkeypatch.setattr(time, "strftime", mockreturn)
    assert pyatmo.helpers.today_stamps() == expected
