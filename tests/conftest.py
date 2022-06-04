"""Define shared fixtures."""
# pylint: disable=redefined-outer-name, protected-access
import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import pyatmo

from .common import MockResponse, fake_post_request


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def auth(requests_mock):
    """Auth fixture."""
    with open("fixtures/oauth2_token.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.AUTH_REQ_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    return pyatmo.ClientAuth(
        client_id="CLIENT_ID",
        client_secret="CLIENT_SECRET",
        username="USERNAME",
        password="PASSWORD",
        scope=" ".join(pyatmo.const.ALL_SCOPES),
    )


@pytest.fixture(scope="function")
def home_data(auth, requests_mock):
    """HomeData fixture."""
    with open("fixtures/home_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESDATA_ENDPOINT,
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
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMESTATUS_ENDPOINT,
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
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETPUBLIC_DATA_ENDPOINT,
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
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETSTATIONDATA_ENDPOINT,
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
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMECOACHDATA_ENDPOINT,
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
            f"{vpn_url}/command/ping",
            json=json_fixture,
            headers={"content-type": "application/json"},
        )

    local_url = "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    with open("fixtures/camera_ping.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        f"{local_url}/command/ping",
        json=json_fixture,
        headers={"content-type": "application/json"},
    )


@pytest.fixture(scope="function")
def camera_home_data(auth, camera_ping, requests_mock):  # pylint: disable=W0613
    """CameraHomeData fixture."""
    with open("fixtures/camera_home_data.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETHOMEDATA_ENDPOINT,
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
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_api_request, patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        camera_data = pyatmo.AsyncCameraData(async_auth)
        await camera_data.async_update()

        mock_api_request.assert_called()
        mock_request.assert_called()
        yield camera_data


@pytest.fixture(scope="function")
async def async_home_coach_data(async_auth):
    """AsyncHomeCoacheData fixture."""
    with open("fixtures/home_coach_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        hcd = pyatmo.AsyncHomeCoachData(async_auth)
        await hcd.async_update()

        mock_request.assert_awaited()
        yield hcd


@pytest.fixture(scope="function")
async def async_home_data(async_auth):
    """AsyncHomeData fixture."""
    with open("fixtures/home_data_simple.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)

    mock_resp = MockResponse(json_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
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
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
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
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_resp),
    ) as mock_request:
        wsd = pyatmo.AsyncWeatherStationData(async_auth)
        await wsd.async_update()

        mock_request.assert_called()
        return wsd


@pytest.fixture(scope="function")
async def async_account(async_auth):
    """AsyncAccount fixture."""
    account = pyatmo.AsyncAccount(async_auth)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_post_request,
    ), patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_request",
        fake_post_request,
    ):
        await account.async_update_topology()
        yield account


@pytest.fixture(scope="function")
async def async_home(async_account):
    """AsyncClimate fixture for home_id 91763b24c43d3e344f424e8b."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    yield async_account.homes[home_id]
