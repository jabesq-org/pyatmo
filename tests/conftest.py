"""Define shared fixtures."""
# pylint: disable=redefined-outer-name, protected-access
import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo


@contextmanager
def does_not_raise():
    yield


class MockResponse:
    def __init__(self, text, status):
        self._text = text
        self.status = status

    async def json(self):
        return self._text

    async def read(self):
        return self._text

    async def __aexit__(self, exc_type, exc, traceback):
        pass

    async def __aenter__(self):
        return self


@pytest.fixture(scope="function")
def auth(requests_mock):
    """Auth fixture."""
    with open("fixtures/oauth2_token.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.auth.AUTH_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.ClientAuth(
        client_id="CLIENT_ID",
        client_secret="CLIENT_SECRET",
        username="USERNAME",
        password="PASSWORD",
        scope=" ".join(pyatmo.auth.ALL_SCOPES),
    )


@pytest.fixture(scope="function")
def home_data(auth, requests_mock):
    """HomeData fixture."""
    with open("fixtures/home_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_data = pyatmo.HomeData(auth)
    home_data.update()
    return home_data


@pytest.fixture(scope="function")
def home_status(auth, home_id, requests_mock):
    """HomeStatus fixture."""
    with open("fixtures/home_status_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.thermostat._GETHOMESTATUS_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    home_status = pyatmo.HomeStatus(auth, home_id)
    home_status.update()
    return home_status


@pytest.fixture(scope="function")
def public_data(auth, requests_mock):
    """PublicData fixture."""
    with open("fixtures/public_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.public_data._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )

    lon_ne = str(6.221652)
    lat_ne = str(46.610870)
    lon_sw = str(6.217828)
    lat_sw = str(46.596485)

    public_data = pyatmo.PublicData(auth, lat_ne, lon_ne, lat_sw, lon_sw)
    public_data.update()
    return public_data


@pytest.fixture(scope="function")
def weather_station_data(auth, requests_mock):
    """WeatherStationData fixture."""
    with open(
        "fixtures/weatherstation_data_simple.json",
        encoding="utf-8",
    ) as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.weather_station._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    wsd = pyatmo.WeatherStationData(auth)
    wsd.update()
    return wsd


@pytest.fixture(scope="function")
def home_coach_data(auth, requests_mock):
    """HomeCoachData fixture."""
    with open("fixtures/home_coach_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.home_coach._GETHOMECOACHDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    hcd = pyatmo.HomeCoachData(auth)
    hcd.update()
    return hcd


@pytest.fixture(scope="function")
def camera_ping(requests_mock):
    """Camera ping fixture."""
    for index in ["w", "z", "g"]:
        vpn_url = (
            f"https://prodvpn-eu-2.netatmo.net/restricted/10.255.248.91/"
            f"6d278460699e56180d47ab47169efb31/"
            f"MpEylTU2MDYzNjRVD-LJxUnIndumKzLboeAwMDqTT{index},,"
        )
        with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
            json_fixture = json.load(json_file)
        requests_mock.post(
            vpn_url + "/command/ping",
            json=json_fixture,
            headers={"content-type": "application/json"},
        )
    local_url = "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        local_url + "/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )


@pytest.fixture(scope="function")
def camera_home_data(auth, camera_ping, requests_mock):
    """CameraHomeData fixture."""
    with open("fixtures/camera_home_data.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.camera._GETHOMEDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    camera_data = pyatmo.CameraData(auth)
    camera_data.update()
    return camera_data


@pytest.fixture(scope="function")
async def async_auth():
    """AsyncAuth fixture."""
    with patch("pyatmo.auth.AbstractAsyncAuth", AsyncMock()) as auth:
        yield auth


@pytest.fixture(scope="function")
async def async_camera_home_data(async_auth):
    """AsyncCameraHomeData fixture."""
    with open("fixtures/camera_home_data.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        camera_data = pyatmo.AsyncCameraData(async_auth)
        await camera_data.async_update()

        mock_request.assert_called()
        yield camera_data


@pytest.fixture(scope="function")
async def async_home_coach_data(async_auth):
    """AsyncHomeCoacheData fixture."""
    with open("fixtures/home_coach_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        hcd = pyatmo.AsyncHomeCoachData(async_auth)
        await hcd.async_update()

        mock_request.assert_called()
        yield hcd


@pytest.fixture(scope="function")
async def async_home_data(async_auth):
    """AsyncHomeData fixture."""
    with open("fixtures/home_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        home_data = pyatmo.AsyncHomeData(async_auth)
        await home_data.async_update()

        mock_request.assert_called()
        return home_data


@pytest.fixture(scope="function")
async def async_home_status(async_auth, home_id):
    """AsyncHomeStatus fixture."""
    with open("fixtures/home_status_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        home_status = pyatmo.AsyncHomeStatus(async_auth, home_id)
        await home_status.async_update()

        mock_request.assert_called()
        return home_status


@pytest.fixture(scope="function")
async def async_weather_station_data(async_auth):
    """AsyncWeatherStationData fixture."""
    with open(
        "fixtures/weatherstation_data_simple.json",
        encoding="utf-8",
    ) as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        wsd = pyatmo.AsyncWeatherStationData(async_auth)
        await wsd.async_update()

        mock_request.assert_called()
        return wsd
