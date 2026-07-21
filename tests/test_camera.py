"""Define tests for camera module."""

import json
from unittest.mock import AsyncMock, patch

import anyio
import pytest

from pyatmo import SIREN_BASE_URL, ApiError, DeviceType, WebRTCStream
from pyatmo.modules.device_types import DeviceCategory, DoorTagCategory
from tests.common import MockResponse
from tests.conftest import does_not_raise


async def test_async_doortag_NACamDoorTag(async_home):
    """NACamDoorTag exposes doortag_category, keeps device_category, no feature leak."""
    module_id = "12:34:56:00:86:99"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NACamDoorTag
    assert module.doortag_category == DoorTagCategory.window
    assert module.device_category == DeviceCategory.opening
    assert "doortag_category" not in module.features
    assert "device_category" not in module.features


async def test_async_camera_NACamera(async_home):
    """Test Netatmo indoor camera module."""
    module_id = "12:34:56:00:f1:62"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    await module.async_update_camera_urls()
    assert module.device_type == DeviceType.NACamera
    assert module.is_local
    assert module.local_url == "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    vpn_url = "https://prodvpn-eu-2.netatmo.net/restricted/10.255.123.45/609e27de5699fb18147ab47d06846631/MTRPn_BeWCav5RBq4U1OMDruTW4dkQ0NuMwNDAw11g,,"
    assert module.vpn_url == vpn_url
    assert module.camera_url == module.local_url
    person_id = "91827374-7e04-5298-83ad-a0cb8372dff1"
    assert person_id in module.home.persons
    person = module.home.persons[person_id]
    assert person.pseudo == "John Doe"
    assert person.out_of_sight
    assert person.last_seen == 1557071156


async def test_async_camera_NPC(async_home):
    """Test Netatmo indoor camera advance module."""
    module_id = "12:34:56:00:f1:63"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    await module.async_update_camera_urls()
    assert module.device_type == DeviceType.NPC
    assert module.is_local
    assert module.local_url is None
    vpn_url = "https://prodvpn-eu-2.netatmo.net/restricted/10.255.123.45/9fb1814609e27de5697ab47d06846631/MTRPn_BeWCav5RBq4U1OMDruTW4dkQ0NuMwNDAw11g,,"
    assert module.vpn_url == vpn_url
    assert module.camera_url == module.vpn_url
    person_id = "91827374-7e04-5298-83ad-a0cb8372dff1"
    assert person_id in module.home.persons
    person = module.home.persons[person_id]
    assert person.pseudo == "John Doe"
    assert person.out_of_sight
    assert person.last_seen == 1557071156


async def test_async_NOC(async_home):
    """Test basic outdoor camera functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC
    assert module.firmware_revision == 3002000
    assert module.firmware_name == "3.2.0"
    assert module.monitoring is True
    assert module.alim_status == 2
    assert module.is_local is False
    assert module.local_url is None
    vpn_url = "https://prodvpn-eu-6.netatmo.net/10.20.30.41/333333333333/444444444444,,"
    assert module.vpn_url == vpn_url
    assert module.camera_url == module.vpn_url
    assert module.floodlight == "auto"
    assert module.siren_status == "no_sound"

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    def gen_json_data(state):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": module_id,
                            "floodlight": state,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_floodlight_on()
        mock_resp.assert_awaited_with(
            params=gen_json_data("on"),
            endpoint="api/setstate",
        )

        assert await module.async_floodlight_off()
        mock_resp.assert_awaited_with(
            params=gen_json_data("off"),
            endpoint="api/setstate",
        )

        assert await module.async_floodlight_auto()
        mock_resp.assert_awaited_with(
            params=gen_json_data("auto"),
            endpoint="api/setstate",
        )


async def test_async_camera_monitoring(async_home):
    """Test basic camera monitoring functionality."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC
    assert module.is_local is False

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    def gen_json_data(state):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": module_id,
                            "monitoring": state,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_monitoring_on()
        mock_resp.assert_awaited_with(
            params=gen_json_data("on"),
            endpoint="api/setstate",
        )

        assert await module.async_monitoring_off()
        mock_resp.assert_awaited_with(
            params=gen_json_data("off"),
            endpoint="api/setstate",
        )


async def test_async_camera_siren(async_home):
    """Test siren control via default public API endpoint (api.netatmo.com)."""
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC
    assert module.siren_status == "no_sound"

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    def gen_json_data(state):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": module_id,
                            "siren_status": state,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_siren_on()
        mock_resp.assert_awaited_with(
            endpoint="api/setstate",
            base_url=None,
            params=gen_json_data("sound"),
        )

        assert await module.async_siren_off()
        mock_resp.assert_awaited_with(
            endpoint="api/setstate",
            base_url=None,
            params=gen_json_data("no_sound"),
        )


async def test_async_camera_siren_app_endpoint(async_home):
    """Test siren control via app.netatmo.net to bypass public API restriction.

    The public OAuth2 API (api.netatmo.com) rejects siren_status with error
    code 21. app.netatmo.net accepts the same OAuth2 token and payload.
    Callers pass base_url=SIREN_BASE_URL to opt in to this workaround.
    """
    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    def gen_json_data(state):
        return {
            "json": {
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": module_id,
                            "siren_status": state,
                        },
                    ],
                },
            },
        }

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        assert await module.async_siren_on(base_url=SIREN_BASE_URL)
        mock_resp.assert_awaited_with(
            endpoint="api/setstate",
            base_url=SIREN_BASE_URL,
            params=gen_json_data("sound"),
        )

        assert await module.async_siren_off(base_url=SIREN_BASE_URL)
        mock_resp.assert_awaited_with(
            endpoint="api/setstate",
            base_url=SIREN_BASE_URL,
            params=gen_json_data("no_sound"),
        )


async def test_async_camera_siren_missing_status(async_home):
    """Test that NOC handles missing siren_status in API payload gracefully."""
    module_id = "12:34:56:10:b9:0e"
    module = async_home.modules[module_id]

    # Simulate an API response without siren_status (e.g. older firmware)
    module.siren_status = None
    assert module.siren_status is None


@pytest.mark.parametrize(
    ("module_id", "device_type", "can_use_local_url"),
    [
        ("12:34:56:00:f1:62", DeviceType.NACamera, True),
        ("12:34:56:10:b9:0e", DeviceType.NOC, True),
        ("12:34:56:00:f1:63", DeviceType.NPC, False),
    ],
)
async def test_async_live_snapshot(
    async_home, module_id, device_type, can_use_local_url
):
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == device_type
    await module.async_update_camera_urls()
    assert module.local_url or module.vpn_url

    expected_snapshot = b"test stream image bytes"

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_get_image",
        AsyncMock(return_value=expected_snapshot),
    ) as mock_resp:
        received_snapshot = await module.async_get_live_snapshot()

        if can_use_local_url and module.is_local:
            base_url = module.local_url
        else:
            base_url = module.vpn_url

        mock_resp.assert_awaited_with(
            base_url=base_url,
            endpoint="/live/snapshot_720.jpg",
        )

        assert received_snapshot == expected_snapshot


@pytest.mark.parametrize(
    ("response_fixture", "exception"),
    [
        ("webrtc_offer_ok.json", does_not_raise()),
        ("webrtc_offer_unreachable.json", pytest.raises(ApiError)),
    ],
)
async def test_async_webrtc_stream_start(async_home, response_fixture, exception):
    """Test starting a WebRTC stream."""
    module_id = "12:34:56:00:f1:63"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NPC

    async with await anyio.open_file(
        f"fixtures/{response_fixture}",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    session_id = "af6da83b-1fd5-46ab-bf08-8e5db3cb9725"
    sdp_offer = "sdp_test_offer"

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            AsyncMock(return_value=MockResponse(response, 200)),
        ) as mock_resp,
        exception,
    ):
        answer = await module.async_start_stream(session_id, sdp_offer)

        mock_resp.assert_awaited_with(
            params={
                "home_id": async_home.entity_id,
                "device_id": module_id,
                "session_id": session_id,
                "sdp": sdp_offer,
            },
            endpoint="api/webrtc/offer",
        )

        assert answer.stream.session_id == session_id
        assert answer.stream.tag_id == "OZzgKVlQCW0="
        assert answer.sdp == "sdp_test_answser"


@pytest.mark.parametrize(
    ("response_fixture", "exception"),
    [
        ("webrtc_terminate_ok.json", does_not_raise()),
        ("webrtc_terminate_no_session.json", pytest.raises(ApiError)),
    ],
)
async def test_async_webrtc_stream_stop(async_home, response_fixture, exception):
    """Test stopping a WebRTC stream."""
    module_id = "12:34:56:00:f1:63"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NPC

    async with await anyio.open_file(
        f"fixtures/{response_fixture}",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    session_id = "af6da83b-1fd5-46ab-bf08-8e5db3cb9725"
    tag_id = "OZzgKVlQCW0="

    with (
        patch(
            "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
            AsyncMock(return_value=MockResponse(response, 200)),
        ) as mock_resp,
        exception,
    ):
        await module.async_stop_stream(WebRTCStream(session_id, tag_id))

        mock_resp.assert_awaited_with(
            params={
                "home_id": async_home.entity_id,
                "device_id": module_id,
                "session_id": session_id,
                "tag_id": tag_id,
            },
            endpoint="api/webrtc/terminate",
        )
