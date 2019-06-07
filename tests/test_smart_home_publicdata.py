"""Define tests for Public weather module."""
import json

import pytest

import smart_home.PublicData


def test_PublicData(auth, requests_mock):
    with open("fixtures/public_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.PublicData._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    publicData = smart_home.PublicData.PublicData(auth)
    assert publicData.status == "ok"


def test_PublicData_unavailable(auth, requests_mock):
    requests_mock.post(smart_home.PublicData._GETPUBLIC_DATA, status_code=404)
    with pytest.raises(smart_home.PublicData.NoDevice):
        smart_home.PublicData.PublicData(auth)


def test_PublicData_error(auth, requests_mock):
    with open("fixtures/public_data_error_mongo.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.PublicData._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.PublicData.NoDevice):
        smart_home.PublicData.PublicData(auth)
