"""Define tests for untility methods."""
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
