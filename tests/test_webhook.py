"""Tests for webhook payload processing."""

from __future__ import annotations

import pytest

import pyatmo
from pyatmo.helpers import number_or_none, str_or_none
from pyatmo.room import Room
from pyatmo.webhook import (
    _ROOM_SETPOINT_KEYS,
    LifecycleStatus,
    WebhookEvent,
    WebhookKind,
    WebhookResult,
    build_webhook_event,
    classify,
    process_webhook,
    resolve_home_id,
)


def test_webhook_result_defaults():
    result = WebhookResult(
        home_id="h1",
        event_type="set_point",
        push_type="display_change",
        kind=WebhookKind.STATE,
    )
    assert result.touched_ids == []
    assert result.events == []
    assert result.needs_refresh is False
    assert result.lifecycle is None


def test_webhook_event_defaults():
    event = WebhookEvent(event_type="person", push_type="NACamera-person", home_id="h1")
    assert event.person_ids == []
    assert event.raw == {}
    assert event.camera_id is None


def test_webhook_types_exported_from_package():
    assert pyatmo.WebhookResult is WebhookResult
    assert pyatmo.WebhookKind is WebhookKind
    assert pyatmo.WebhookEvent is WebhookEvent
    assert pyatmo.LifecycleStatus is LifecycleStatus


@pytest.mark.parametrize(
    ("event_type", "push_type", "expected"),
    [
        ("set_point", "display_change", WebhookKind.STATE),
        ("cancel_set_point", "display_change", WebhookKind.STATE),
        ("therm_mode", "home_event_changed", WebhookKind.STATE),
        ("on", "NACamera-on", WebhookKind.STATE),
        ("off", "NACamera-off", WebhookKind.STATE),
        ("light_mode", "NOC-light_mode", WebhookKind.STATE),
        ("schedule", "home_event_changed", WebhookKind.TOPOLOGY_DIRTY),
        ("person", "NACamera-person", WebhookKind.EVENT),
        ("movement", "NACamera-movement", WebhookKind.EVENT),
        ("disconnection", "NACamera-disconnection", WebhookKind.EVENT),
        (None, "webhook_activation", WebhookKind.LIFECYCLE),
        (None, "webhook_deactivation", WebhookKind.LIFECYCLE),
        ("connection", "NACamera-connection", WebhookKind.LIFECYCLE),
        ("something_new", "brand_new_push", WebhookKind.UNKNOWN),
    ],
)
def test_classify(event_type, push_type, expected):
    assert classify(event_type, push_type) is expected


def test_resolve_home_id_top_level():
    assert resolve_home_id({"home_id": "top"}) == "top"


def test_resolve_home_id_nested():
    assert resolve_home_id({"home": {"id": "nested"}}) == "nested"


def test_resolve_home_id_top_level_wins_over_nested():
    assert resolve_home_id({"home_id": "top", "home": {"id": "nested"}}) == "top"


def test_resolve_home_id_missing():
    assert resolve_home_id({"event_type": "on"}) is None


def test_build_webhook_event_person():
    payload = {
        "persons": [
            {"id": "p1", "is_known": True},
            {"id": "p2", "is_known": False},
        ],
        "snapshot_url": "https://example/snap",
        "event_type": "person",
        "camera_id": "cam1",
        "device_id": "cam1",
        "home_id": "h1",
        "message": "seen",
        "push_type": "NACamera-person",
    }
    event = build_webhook_event(payload)
    assert event.event_type == "person"
    assert event.push_type == "NACamera-person"
    assert event.home_id == "h1"
    assert event.camera_id == "cam1"
    assert event.person_ids == ["p1", "p2"]
    assert event.snapshot_url == "https://example/snap"
    assert event.message == "seen"
    assert event.raw is payload


async def test_process_webhook_activation(async_account):
    result = await process_webhook(async_account, {"push_type": "webhook_activation"})
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.ACTIVATION
    assert result.needs_refresh is False


async def test_process_webhook_deactivation(async_account):
    result = await process_webhook(
        async_account,
        {"push_type": "webhook_deactivation"},
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.DEACTIVATION


async def test_process_webhook_camera_connection_needs_refresh(async_account):
    result = await process_webhook(
        async_account,
        {"push_type": "NACamera-connection"},
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.CONNECTION
    assert result.needs_refresh is True


async def test_process_webhook_unknown(async_account):
    result = await process_webhook(
        async_account,
        {"event_type": "brand_new", "push_type": "brand_new_push"},
    )
    assert result.kind is WebhookKind.UNKNOWN
    assert result.touched_ids == []


async def test_process_webhook_malformed_no_event(async_account):
    result = await process_webhook(async_account, {})
    assert result.kind is WebhookKind.UNKNOWN


async def test_process_webhook_person_event(async_account):
    payload = {
        "persons": [{"id": "91827374-7e04-5298-83ad-a0cb8372dff1", "is_known": True}],
        "snapshot_url": "https://example/snap",
        "event_type": "person",
        "camera_id": "12:34:56:00:f1:62",
        "device_id": "12:34:56:00:f1:62",
        "home_id": "91763b24c43d3e344f424e8b",
        "message": "MYHOME: John Doe has been seen",
        "push_type": "NACamera-person",
    }
    result = await process_webhook(async_account, payload)
    assert result.kind is WebhookKind.EVENT
    assert result.touched_ids == ["12:34:56:00:f1:62"]
    assert len(result.events) == 1
    event = result.events[0]
    assert event.event_type == "person"
    assert event.person_ids == ["91827374-7e04-5298-83ad-a0cb8372dff1"]


async def test_process_webhook_movement_event(async_account):
    payload = {
        "event_type": "movement",
        "device_id": "12:34:56:00:f1:62",
        "camera_id": "12:34:56:00:f1:62",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NACamera-movement",
    }
    result = await process_webhook(async_account, payload)
    assert result.kind is WebhookKind.EVENT
    assert result.events[0].event_type == "movement"
    assert result.touched_ids == ["12:34:56:00:f1:62"]


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_updates_room(async_account):
    # async_home loads status for this home; async_account is its parent.
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_setpoint_mode == "away"  # precondition from fixture
    assert room.therm_measured_temperature == 19.8  # precondition from fixture
    assert room.reachable is True  # precondition from fixture

    payload = {
        "room_id": "2746182631",
        "home": {
            "id": home_id,
            "name": "MYHOME",
            "rooms": [
                {
                    "id": "2746182631",
                    "name": "Livingroom",
                    "type": "livingroom",
                    "therm_setpoint_mode": "manual",
                    "therm_setpoint_temperature": 21,
                    "therm_setpoint_end_time": 1612734552,
                },
            ],
            "modules": [
                {"id": "12:34:56:00:01:ae", "name": "Livingroom", "type": "NATherm1"},
            ],
        },
        "mode": "manual",
        "event_type": "set_point",
        "temperature": 21,
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == ["2746182631"]
    assert room.therm_setpoint_mode == "manual"
    assert room.therm_setpoint_temperature == 21
    # Telemetry not present in the webhook payload must be preserved, not wiped.
    assert room.therm_measured_temperature == 19.8
    assert room.reachable is True


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_partial_room_match(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]

    payload = {
        "event_type": "set_point",
        "home": {
            "id": home_id,
            "rooms": [
                {"id": "2746182631", "therm_setpoint_mode": "manual"},
                {"id": "does-not-exist", "therm_setpoint_mode": "max"},
            ],
        },
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == ["2746182631"]
    assert room.therm_setpoint_mode == "manual"


@pytest.mark.usefixtures("async_home")
@pytest.mark.parametrize("home_block", [None, "x"])
async def test_process_webhook_set_point_without_usable_home_block(
    async_account,
    home_block,
):
    payload = {
        "event_type": "set_point",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "display_change",
    }
    if home_block is not None:
        payload["home"] = home_block

    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


async def test_process_webhook_set_point_unknown_home_no_mutation(async_account):
    payload = {
        "home": {"id": "does-not-exist", "rooms": [{"id": "r1"}], "modules": []},
        "event_type": "set_point",
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)
    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_therm_mode_updates_home(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    assert home.therm_mode == "schedule"  # precondition from fixture

    payload = {
        "event_type": "therm_mode",
        "home": {"id": home_id, "therm_mode": "hg"},
        "mode": "hg",
        "previous_mode": "schedule",
        "push_type": "home_event_changed",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == [home_id]
    assert home.therm_mode == "hg"


@pytest.mark.usefixtures("async_home")
@pytest.mark.parametrize(
    "home_block",
    [None, "x", {"id": "91763b24c43d3e344f424e8b"}],
)
async def test_process_webhook_therm_mode_without_mode_touches_nothing(
    async_account,
    home_block,
):
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    assert home.therm_mode == "schedule"  # precondition from fixture

    payload = {
        "event_type": "therm_mode",
        "home_id": home_id,
        "push_type": "home_event_changed",
    }
    if home_block is not None:
        payload["home"] = home_block

    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert home.therm_mode == "schedule"


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_off(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:f1:62"
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.monitoring is True  # precondition from fixture

    payload = {
        "event_type": "off",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NACamera-off",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == [camera_id]
    assert camera.monitoring is False


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_on(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:f1:62"
    camera = async_account.homes[home_id].modules[camera_id]
    camera.monitoring = False

    payload = {
        "event_type": "on",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NACamera-on",
    }
    result = await process_webhook(async_account, payload)
    assert camera.monitoring is True
    assert result.touched_ids == [camera_id]


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_light_mode(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:10:b9:0e"  # NOC, has floodlight attr
    camera = async_account.homes[home_id].modules[camera_id]

    payload = {
        "event_type": "light_mode",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NOC-light_mode",
        "sub_type": "on",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == [camera_id]
    assert camera.floodlight == "on"


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_light_mode_no_floodlight_attr(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:01:ae"  # NATherm1, has no floodlight attr

    payload = {
        "event_type": "light_mode",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NOC-light_mode",
        "sub_type": "on",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_light_mode_unresolvable_camera(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "99:99:99:99:99:99"

    payload = {
        "event_type": "light_mode",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NOC-light_mode",
        "sub_type": "on",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_on_unresolvable_camera(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "99:99:99:99:99:99"

    payload = {
        "event_type": "on",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NACamera-on",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_off_unresolvable_camera(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "99:99:99:99:99:99"

    payload = {
        "event_type": "off",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NACamera-off",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
@pytest.mark.parametrize("event_type", ["on", "off"])
async def test_process_webhook_camera_monitoring_without_camera_id(
    async_account,
    event_type,
):
    payload = {
        "event_type": event_type,
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": f"NACamera-{event_type}",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_light_mode_without_camera_id(async_account):
    payload = {
        "event_type": "light_mode",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NOC-light_mode",
        "sub_type": "on",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
@pytest.mark.parametrize("sub_type_block", [{}, {"sub_type": None}])
async def test_process_webhook_light_mode_without_sub_type_keeps_value(
    async_account,
    sub_type_block,
):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:10:b9:0e"  # NOC, has floodlight attr
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.floodlight == "auto"  # precondition from fixture

    payload = {
        "event_type": "light_mode",
        "device_id": camera_id,
        "camera_id": camera_id,
        "home_id": home_id,
        "push_type": "NOC-light_mode",
    }
    payload.update(sub_type_block)

    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert camera.floodlight == "auto"


async def test_process_webhook_malformed_non_dict_home_no_raise(async_account):
    payload = {
        "event_type": "on",
        "home": "x",
        "push_type": "NACamera-on",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


async def test_process_webhook_schedule_needs_refresh(async_account):
    payload = {
        "event_type": "schedule",
        "schedule_id": "b1b54a2f45795764f59d50d8",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "home_event_changed",
    }
    result = await process_webhook(async_account, payload)
    assert result.kind is WebhookKind.TOPOLOGY_DIRTY
    assert result.needs_refresh is True
    assert result.touched_ids == []


async def test_account_process_webhook_delegates(async_account):
    result = await async_account.process_webhook({"push_type": "webhook_activation"})
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.ACTIVATION


@pytest.mark.parametrize(
    "event_type",
    [
        "hush",
        "smoke",
        "co_detected",
        "tampered",
        "detection_chamber_status",
        "sound_test",
        "siren_sounding",
        "siren_tampered",
        "incoming_call",
        "accepted_call",
        "missed_call",
        "sd",
        "alim",
        "boot",
        "new_module",
        "module_low_battery",
        "module_end_update",
        "tag_uninstalled",
        "daily_summary",
        "human",
        "animal",
        "vehicle",
        "alarm_started",
    ],
)
def test_classify_full_event_stream_catalog(event_type):
    # Smoke/siren/doorbell/tag/health/module events surface as EVENT, not UNKNOWN.
    assert classify(event_type, f"NSD-{event_type}") is WebhookKind.EVENT


@pytest.mark.parametrize("event_type", ["on", "off"])
def test_classify_on_off_stay_state(event_type):
    # on/off are in the EventTypes enum but must remain STATE, not EVENT.
    assert classify(event_type, f"NACamera-{event_type}") is WebhookKind.STATE


@pytest.mark.parametrize(
    "persons",
    [None, "abc", ["x"], [1, 2], {"id": "p1"}],
)
async def test_process_webhook_malformed_persons_no_raise(async_account, persons):
    payload = {
        "event_type": "person",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NACamera-person",
        "persons": persons,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.EVENT
    assert result.touched_ids == []
    assert result.events[0].person_ids == []


@pytest.mark.parametrize("rooms", [None, ["x"]])
async def test_process_webhook_malformed_rooms_no_raise(async_account, rooms):
    payload = {
        "event_type": "set_point",
        "home": {"id": "91763b24c43d3e344f424e8b", "rooms": rooms},
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []


async def test_process_webhook_event_touched_ids_from_module_id(async_account):
    payload = {
        "event_type": "module_low_battery",
        "module_id": "12:34:56:00:01:ae",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NATherm1-module_low_battery",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.EVENT
    assert result.touched_ids == ["12:34:56:00:01:ae"]
    assert result.events[0].module_id == "12:34:56:00:01:ae"


async def test_process_webhook_event_touched_ids_are_strings(async_account):
    payload = {
        "event_type": "movement",
        "device_id": {"a": 1},
        "camera_id": "12:34:56:00:f1:62",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NACamera-movement",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.EVENT
    assert all(isinstance(touched_id, str) for touched_id in result.touched_ids)
    assert result.touched_ids == ["12:34:56:00:f1:62"]


async def test_process_webhook_smoke_event_surfaced(async_account):
    payload = {
        "event_type": "smoke",
        "device_id": "12:34:56:00:e3:9b",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NSD-smoke",
    }
    result = await process_webhook(async_account, payload)
    assert result.kind is WebhookKind.EVENT
    assert result.events[0].event_type == "smoke"
    assert result.touched_ids == ["12:34:56:00:e3:9b"]


@pytest.mark.usefixtures("async_home")
@pytest.mark.parametrize(
    "payload",
    [
        {"event_type": ["on"], "push_type": "NACamera-on"},
        {"event_type": "movement", "push_type": ["x"]},
        {"event_type": "set_point", "push_type": "display_change", "home_id": {"a": 1}},
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {"id": ["x"]},
        },
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {
                "id": "91763b24c43d3e344f424e8b",
                "rooms": [{"id": ["2746182631"], "therm_setpoint_mode": "manual"}],
            },
        },
        {
            "event_type": "on",
            "push_type": "NACamera-on",
            "home_id": "91763b24c43d3e344f424e8b",
            "camera_id": {"a": 1},
        },
        {
            "event_type": "off",
            "push_type": "NACamera-off",
            "home_id": "91763b24c43d3e344f424e8b",
            "device_id": ["x"],
        },
        {
            "event_type": "light_mode",
            "push_type": "NOC-light_mode",
            "home_id": "91763b24c43d3e344f424e8b",
            "camera_id": {"a": 1},
            "sub_type": "on",
        },
    ],
)
async def test_process_webhook_unhashable_scalar_no_raise(async_account, payload):
    """An unhashable value in any looked-up field must not raise."""
    result = await process_webhook(async_account, payload)

    assert result.touched_ids == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_non_str_sub_type_keeps_model_clean(async_account):
    """A malformed sub_type must not land on the module's floodlight attribute."""
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:10:b9:0e"  # NOC, has floodlight attr
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.floodlight == "auto"  # precondition from fixture

    result = await process_webhook(
        async_account,
        {
            "event_type": "light_mode",
            "push_type": "NOC-light_mode",
            "home_id": home_id,
            "camera_id": camera_id,
            "sub_type": {"evil": 1},
        },
    )

    assert result.touched_ids == []
    assert camera.floodlight == "auto"


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_non_str_therm_mode_keeps_model_clean(async_account):
    """A malformed therm_mode must not land on the home's therm_mode attribute."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    assert home.therm_mode == "schedule"  # precondition from fixture

    result = await process_webhook(
        async_account,
        {
            "event_type": "therm_mode",
            "push_type": "home_event_changed",
            "home": {"id": home_id, "therm_mode": [1, 2]},
        },
    )

    assert result.touched_ids == []
    assert home.therm_mode == "schedule"


async def test_process_webhook_person_ids_are_strings(async_account):
    """Non-string person ids are dropped, matching the touched_ids guard."""
    result = await process_webhook(
        async_account,
        {
            "event_type": "person",
            "push_type": "NACamera-person",
            "home_id": "91763b24c43d3e344f424e8b",
            "persons": [{"id": 7}, {"id": None}, "junk", {"id": "p1"}],
        },
    )

    assert result.events[0].person_ids == ["p1"]


async def test_process_webhook_event_id_fields_are_strings(async_account):
    """A non-string id is dropped from the event too, not just from touched_ids."""
    result = await process_webhook(
        async_account,
        {
            "event_type": "movement",
            "push_type": "NACamera-movement",
            "home_id": "91763b24c43d3e344f424e8b",
            "device_id": {"a": 1},
            "camera_id": "12:34:56:00:f1:62",
        },
    )

    assert result.events[0].device_id is None
    assert result.events[0].camera_id == "12:34:56:00:f1:62"
    assert result.touched_ids == ["12:34:56:00:f1:62"]


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_rejects_wrongly_typed_values(async_account):
    """A malformed setpoint value is dropped, preserving the known-good value."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_setpoint_mode == "away"  # precondition from fixture
    assert room.therm_setpoint_temperature == 12  # precondition from fixture

    result = await process_webhook(
        async_account,
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {
                "id": home_id,
                "rooms": [
                    {
                        "id": "2746182631",
                        "therm_setpoint_mode": {"evil": 1},
                        "therm_setpoint_temperature": "hot",
                    },
                ],
            },
        },
    )

    assert result.touched_ids == []
    assert room.therm_setpoint_mode == "away"
    assert room.therm_setpoint_temperature == 12


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_does_not_alias_payload_values(async_account):
    """A mutable payload value must never be stored on the model."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    shared = [1, 2]

    await process_webhook(
        async_account,
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {
                "id": home_id,
                "rooms": [{"id": "2746182631", "therm_setpoint_end_time": shared}],
            },
        },
    )

    assert room.therm_setpoint_end_time is not shared


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_explicit_null_clears_value(async_account):
    """An explicit `null` clears the field; only wrong types are rejected."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_setpoint_mode == "away"  # precondition from fixture

    result = await process_webhook(
        async_account,
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {
                "id": home_id,
                "rooms": [{"id": "2746182631", "therm_setpoint_mode": None}],
            },
        },
    )

    assert result.touched_ids == ["2746182631"]
    assert room.therm_setpoint_mode is None


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_keeps_falsy_values(async_account):
    """`0` is a valid setpoint value and must not be skipped as falsy."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]

    result = await process_webhook(
        async_account,
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {
                "id": home_id,
                "rooms": [{"id": "2746182631", "therm_setpoint_temperature": 0}],
            },
        },
    )

    assert result.touched_ids == ["2746182631"]
    assert room.therm_setpoint_temperature == 0


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_without_setpoint_keys_reports_nothing(
    async_account,
):
    """A resolved room carrying no setpoint keys is not reported as touched."""
    home_id = "91763b24c43d3e344f424e8b"

    result = await process_webhook(
        async_account,
        {
            "event_type": "set_point",
            "push_type": "display_change",
            "home": {
                "id": home_id,
                "rooms": [{"id": "2746182631", "name": "Livingroom"}],
            },
        },
    )

    assert result.touched_ids == []


def test_room_setpoint_keys_match_room_annotations():
    """Every coercer matches the type `Room` declares for that field.

    `_ROOM_SETPOINT_KEYS` duplicates type knowledge that already lives on
    `Room`, so drift would silently reject a valid value rather than fail. This
    pins the two together. Read `__annotations__` directly: `get_type_hints`
    cannot resolve `Room`'s `TYPE_CHECKING`-only names.
    """
    coercer_for = {
        "str|None": str_or_none,
        "int|None": number_or_none,
        "float|None": number_or_none,
    }

    for key, coerce in _ROOM_SETPOINT_KEYS.items():
        declared = Room.__annotations__[key].replace(" ", "")
        assert declared in coercer_for, f"{key}: unhandled declared type {declared!r}"
        assert coerce is coercer_for[declared], (
            f"{key}: Room declares {declared}, but the table coerces with "
            f"{coerce.__name__}"
        )


async def test_process_webhook_never_suspends(async_account):
    """`process_webhook` must run to completion without yielding to the loop.

    Netatmo requires a webhook endpoint to answer immediately and deactivates
    one that does not, so the merge deliberately performs no I/O. Awaiting
    anything here -- an `async_update_*` refresh being the tempting one -- would
    put network latency, including the 429 backoff in `auth.py`, on the response
    path. Driving the coroutine one step must therefore finish it: a suspension
    yields instead of raising `StopIteration`.
    """
    payload = {
        "event_type": "movement",
        "push_type": "NACamera-movement",
        "home_id": "91763b24c43d3e344f424e8b",
        "device_id": "12:34:56:00:f1:62",
    }
    coro = process_webhook(async_account, payload)
    try:
        with pytest.raises(StopIteration):
            coro.send(None)
    finally:
        coro.close()
