"""Define tests for untility methods."""
import time

import pytest
import requests

import smart_home


def test_postRequest_json(requests_mock):
    """Test wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        smart_home._BASE_URL,
        json={"a": "b"},
        headers={"content-type": "application/json"},
    )
    resp = smart_home.postRequest(smart_home._BASE_URL, None)
    assert resp == {"a": "b"}


def test_postRequest_binary(requests_mock):
    """Test wrapper for posting requests against the Netatmo API."""
    requests_mock.post(
        smart_home._BASE_URL,
        text="Success",
        headers={"content-type": "application/text"},
    )
    resp = smart_home.postRequest(smart_home._BASE_URL, None)
    assert resp == b"Success"


@pytest.mark.parametrize("test_input,expected", [(200, None), (404, None)])
def test_postRequest_fail(requests_mock, test_input, expected):
    """Test failing requests against the Netatmo API."""
    requests_mock.post(smart_home._BASE_URL, status_code=test_input)
    resp = smart_home.postRequest(smart_home._BASE_URL, None)
    assert resp is expected


def test_postRequest_timeout(requests_mock):
    """Test failing requests against the Netatmo API with timeouts."""
    requests_mock.post(smart_home._BASE_URL, exc=requests.exceptions.ConnectTimeout)
    with pytest.raises(requests.exceptions.ConnectTimeout):
        assert smart_home.postRequest(smart_home._BASE_URL, None)


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
    assert smart_home.toTimeString(test_input) == expected


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
    assert smart_home.toEpoch(test_input) == expected


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
    assert smart_home.todayStamps() == expected
