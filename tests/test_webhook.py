"""Tests for webhook payload processing."""

from __future__ import annotations

from time import time

import pytest

import pyatmo
from pyatmo.helpers import number_or_none, str_or_none
from pyatmo.room import Room
from pyatmo.webhook import (
    _ROOM_SETPOINT_KEYS,
    LifecycleStatus,
    RefreshScope,
    WebhookEvent,
    WebhookKind,
    WebhookResult,
    build_webhook_events,
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
    assert result.refresh_scope == frozenset()
    assert result.lifecycle is None


def test_webhook_event_defaults():
    event = WebhookEvent(event_type="person", push_type="NACamera-person", home_id="h1")
    assert event.person_id is None
    assert event.person_name is None
    assert event.is_known is None
    assert event.face_url is None
    assert event.room_id is None
    assert event.mode is None
    assert event.vignette_url is None
    assert event.event_id is None
    assert event.raw == {}
    assert event.camera_id is None


def test_webhook_types_exported_from_package():
    assert pyatmo.WebhookResult is WebhookResult
    assert pyatmo.WebhookKind is WebhookKind
    assert pyatmo.WebhookEvent is WebhookEvent
    assert pyatmo.LifecycleStatus is LifecycleStatus
    assert pyatmo.RefreshScope is RefreshScope


@pytest.mark.parametrize(
    ("event_type", "push_type", "expected"),
    [
        ("set_point", "display_change", WebhookKind.STATE),
        ("cancel_set_point", "display_change", WebhookKind.STATE),
        ("setpoint_event", "display_change", WebhookKind.STATE),
        ("therm_mode", "home_event_changed", WebhookKind.STATE),
        ("on", "NACamera-on", WebhookKind.STATE),
        ("off", "NACamera-off", WebhookKind.STATE),
        ("light_mode", "NOC-light_mode", WebhookKind.STATE),
        ("schedule", "home_event_changed", WebhookKind.TOPOLOGY_DIRTY),
        ("person", "NACamera-person", WebhookKind.EVENT),
        ("movement", "NACamera-movement", WebhookKind.EVENT),
        ("disconnection", "NACamera-disconnection", WebhookKind.LIFECYCLE),
        (None, "webhook_activation", WebhookKind.LIFECYCLE),
        (None, "webhook_deactivation", WebhookKind.LIFECYCLE),
        ("connection", "NACamera-connection", WebhookKind.LIFECYCLE),
        ("connection", "connection", WebhookKind.LIFECYCLE),
        ("disconnection", "disconnection", WebhookKind.LIFECYCLE),
        (None, "NPC-connection", WebhookKind.LIFECYCLE),
        (None, "NPC-disconnection", WebhookKind.LIFECYCLE),
        (None, "NACamera-disconnection", WebhookKind.LIFECYCLE),
        (None, "disconnection", WebhookKind.LIFECYCLE),
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


def test_build_webhook_events_person_fan_out():
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
    events = build_webhook_events(payload, home=None)
    assert len(events) == 2

    first, second = events
    assert first.event_type == "person"
    assert first.push_type == "NACamera-person"
    assert first.home_id == "h1"
    assert first.camera_id == "cam1"
    assert first.snapshot_url == "https://example/snap"
    assert first.message == "seen"
    assert first.raw is payload
    assert first.person_id == "p1"
    assert first.is_known is True
    # no home passed -> name unresolved
    assert first.person_name is None

    assert second.person_id == "p2"
    assert second.is_known is False


async def test_process_webhook_activation(async_account):
    result = await process_webhook(async_account, {"push_type": "webhook_activation"})
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.ACTIVATION
    assert result.needs_refresh is False
    assert result.refresh_scope == frozenset()
    assert result.events == []


async def test_process_webhook_deactivation(async_account):
    result = await process_webhook(
        async_account,
        {"push_type": "webhook_deactivation"},
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.DEACTIVATION
    assert result.needs_refresh is False
    assert result.refresh_scope == frozenset()
    assert result.events == []


async def test_process_webhook_camera_connection_needs_refresh(async_account):
    """Bare reconnect: no event_type -> no event."""
    result = await process_webhook(
        async_account,
        {"push_type": "NACamera-connection"},
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.CONNECTION
    assert result.needs_refresh is True
    assert result.refresh_scope == frozenset({RefreshScope.STATUS})
    assert result.events == []


async def test_process_webhook_camera_connection_full_surfaces_event(async_account):
    """Full reconnect payload: event_type present -> surfaces an event."""
    result = await process_webhook(
        async_account,
        {
            "event_type": "connection",
            "push_type": "NACamera-connection",
            "camera_id": "12:34:56:00:f1:62",
            "device_id": "12:34:56:00:f1:62",
            "home_id": "91763b24c43d3e344f424e8b",
        },
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.CONNECTION
    assert result.needs_refresh is True
    assert result.touched_ids == ["12:34:56:00:f1:62"]
    assert len(result.events) == 1
    assert result.events[0].event_type == "connection"


async def test_process_webhook_npc_connection_bare(async_account):
    """NPC (Netatmo Smart Video Doorbell) reconnect, no event_type."""
    result = await process_webhook(async_account, {"push_type": "NPC-connection"})
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.CONNECTION
    assert result.refresh_scope == frozenset({RefreshScope.STATUS})
    assert result.events == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_disconnection_then_connection_flips_reachable(
    async_account,
):
    """Real captures, redacted: disconnection marks unreachable, connection clears it."""
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:f1:62"
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.reachable is True

    result = await process_webhook(
        async_account,
        {
            "event_type": "disconnection",
            "camera_id": camera_id,
            "device_id": camera_id,
            "home_id": home_id,
            "push_type": "disconnection",
        },
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.DISCONNECTION
    assert result.refresh_scope == frozenset()
    assert camera.reachable is False
    assert result.touched_ids == [camera_id]
    assert len(result.events) == 1
    assert result.events[0].event_type == "disconnection"

    result = await process_webhook(
        async_account,
        {
            "event_type": "connection",
            "camera_id": camera_id,
            "device_id": camera_id,
            "home_id": home_id,
            "push_type": "connection",
        },
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.CONNECTION
    assert result.refresh_scope == frozenset({RefreshScope.STATUS})
    assert camera.reachable is True
    assert result.touched_ids == [camera_id]
    assert len(result.events) == 1
    assert result.events[0].event_type == "connection"


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_disconnection_push_type_only(async_account):
    """A `*-disconnection` push type with no event_type must still be LIFECYCLE."""
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:f1:62"
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.reachable is True

    result = await process_webhook(
        async_account,
        {
            "camera_id": camera_id,
            "device_id": camera_id,
            "home_id": home_id,
            "push_type": "NACamera-disconnection",
        },
    )
    assert result.kind is WebhookKind.LIFECYCLE
    assert result.lifecycle is LifecycleStatus.DISCONNECTION
    assert result.refresh_scope == frozenset()
    assert camera.reachable is False
    assert result.touched_ids == [camera_id]
    # No event_type in the payload -> nothing to surface as an event.
    assert result.events == []


async def test_process_webhook_unknown(async_account):
    """An unrecognized event_type still surfaces as an event (S5)."""
    result = await process_webhook(
        async_account,
        {"event_type": "brand_new_thing", "push_type": "brand_new_push"},
    )
    assert result.kind is WebhookKind.UNKNOWN
    assert result.touched_ids == []
    assert len(result.events) == 1
    assert result.events[0].event_type == "brand_new_thing"


async def test_process_webhook_malformed_no_event(async_account):
    result = await process_webhook(async_account, {})
    assert result.kind is WebhookKind.UNKNOWN
    assert result.events == []


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
    assert event.person_id == "91827374-7e04-5298-83ad-a0cb8372dff1"
    assert event.is_known is True
    assert event.person_name == "John Doe"


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
    assert result.refresh_scope == frozenset()


async def test_process_webhook_camera_human_event(async_account):
    """Real camera `human` capture, redacted."""
    payload = {
        "snapshot_id": "6a7ab5a5616f56de6c0ea337",
        "snapshot_url": "https://example/snapshot.jpg",
        "vignette_id": "6a7ab5a5616f56de6c0ea338",
        "vignette_url": "https://example/vignette.jpg",
        "event_type": "human",
        "camera_id": "12:34:56:00:f1:62",
        "device_id": "12:34:56:00:f1:62",
        "home_id": "91763b24c43d3e344f424e8b",
        "event_id": "6a7ab5a5a5d9e433642e230c",
        "message": "Person erfasst Esszimmer",
        "push_type": "NACamera-human",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.EVENT
    assert len(result.events) == 1
    event = result.events[0]
    assert event.event_type == "human"
    assert event.camera_id == "12:34:56:00:f1:62"
    assert event.snapshot_url == "https://example/snapshot.jpg"
    assert event.vignette_url == "https://example/vignette.jpg"
    assert event.event_id == "6a7ab5a5a5d9e433642e230c"
    assert event.message == "Person erfasst Esszimmer"


async def test_process_webhook_person_event_fan_out_two_persons(async_account):
    """One known id (name resolves), one unknown (name stays None)."""
    payload = {
        "persons": [
            {"id": "91827374-7e04-5298-83ad-a0cb8372dff1", "is_known": True},
            {"id": "unknown-person-id-0001", "is_known": False},
        ],
        "event_type": "person",
        "camera_id": "12:34:56:00:f1:62",
        "device_id": "12:34:56:00:f1:62",
        "home_id": "91763b24c43d3e344f424e8b",
        "push_type": "NACamera-person",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.EVENT
    assert len(result.events) == 2

    known, unknown = result.events
    assert known.person_id == "91827374-7e04-5298-83ad-a0cb8372dff1"
    assert known.is_known is True
    assert known.person_name == "John Doe"

    assert unknown.person_id == "unknown-person-id-0001"
    assert unknown.is_known is False
    assert unknown.person_name is None


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_updates_room(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_setpoint_mode == "away"
    assert room.therm_measured_temperature == 19.8
    assert room.reachable is True

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
    # preserved, not wiped
    assert room.therm_measured_temperature == 19.8
    assert room.reachable is True


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_setpoint_event_alias_merges_room(async_account):
    """Real capture: `display_change` uses `setpoint_event`, not `set_point`."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_setpoint_mode == "away"
    assert room.therm_setpoint_temperature == 12
    assert room.therm_measured_temperature == 19.8

    payload = {
        "home": {
            "id": home_id,
            "rooms": [
                {
                    "id": "2746182631",
                    "therm_setpoint_start_time": 1786428433,
                    "therm_setpoint_mode": "manual",
                    "therm_setpoint_end_time": 1786439233,
                    "therm_setpoint_temperature": 13.5,
                },
            ],
        },
        "correlation_id": "3656857635745554143",
        "type": "setpoint_event",
        "home_id": home_id,
        "device_id": "12:34:56:00:bc:24",
        "event_type": "setpoint_event",
        "room_id": "2746182631",
        "mode": "manual",
        "temperature": 13.5,
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == ["2746182631"]
    assert room.therm_setpoint_mode == "manual"
    assert room.therm_setpoint_temperature == 13.5
    # preserved, not wiped
    assert room.therm_measured_temperature == 19.8
    assert len(result.events) == 1
    assert result.events[0].event_type == "setpoint_event"
    assert result.events[0].mode == "manual"


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
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_set_point_unknown_room_self_heals(async_account):
    """A room id that doesn't match any known room adds TOPOLOGY (S4)."""
    home_id = "91763b24c43d3e344f424e8b"

    payload = {
        "event_type": "set_point",
        "home": {
            "id": home_id,
            "rooms": [{"id": "does-not-exist", "therm_setpoint_mode": "manual"}],
        },
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


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
    # Malformed/missing home block -- not evidence of a stale topology.
    assert result.refresh_scope == frozenset()


async def test_process_webhook_set_point_unknown_home_no_mutation(async_account):
    """An unknown home_id self-heals with a TOPOLOGY refresh (S4)."""
    payload = {
        "home": {"id": "does-not-exist", "rooms": [{"id": "r1"}], "modules": []},
        "event_type": "set_point",
        "push_type": "display_change",
    }
    result = await process_webhook(async_account, payload)
    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_therm_mode_updates_home(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    assert home.therm_mode == "schedule"

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
    assert result.refresh_scope == frozenset({RefreshScope.STATUS})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_therm_mode_real_capture_surfaces_event(async_account):
    """Real capture, redacted: STATE result also carries a matching event."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    assert home.therm_mode == "schedule"

    payload = {
        "home_id": home_id,
        "event_type": "therm_mode",
        "home": {"id": home_id, "therm_mode": "away"},
        "mode": "away",
        "push_type": "home_event_changed",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert home.therm_mode == "away"
    assert len(result.events) == 1
    assert result.events[0].event_type == "therm_mode"
    assert result.events[0].mode == "away"


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
    assert home.therm_mode == "schedule"

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
    assert result.refresh_scope == frozenset({RefreshScope.STATUS})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_off(async_account):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:f1:62"
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.monitoring is True

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
    # The module resolved fine, it just doesn't support floodlight -- not a
    # stale topology, so no TOPOLOGY refresh.
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_light_mode_unresolvable_camera(async_account):
    """A camera id that isn't in the home self-heals with TOPOLOGY (S4)."""
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
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_camera_on_unresolvable_camera(async_account):
    """A camera id that isn't in the home self-heals with TOPOLOGY (S4)."""
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
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


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
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


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
    # No camera_id/device_id at all -- nothing was referenced, so nothing to
    # self-heal.
    assert result.refresh_scope == frozenset()


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
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
@pytest.mark.parametrize("sub_type_block", [{}, {"sub_type": None}])
async def test_process_webhook_light_mode_without_sub_type_keeps_value(
    async_account,
    sub_type_block,
):
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:10:b9:0e"  # NOC, has floodlight attr
    camera = async_account.homes[home_id].modules[camera_id]
    assert camera.floodlight == "auto"

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
    assert result.refresh_scope == frozenset(
        {RefreshScope.TOPOLOGY, RefreshScope.STATUS}
    )
    assert result.touched_ids == []


@pytest.mark.parametrize(
    ("payload", "expected_change", "expected_touched"),
    [
        (
            {
                "change": "module_updated",
                "device_id": "12:34:56:3c:63:b2",
                "module_id": "12:34:56:00:01:34:64:98",
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": "12:34:56:00:01:34:64:98",
                            "bridge": "12:34:56:3c:63:b2",
                            "name": "Mobile outlet 1",
                        },
                    ],
                },
                "push_type": "topology_changed",
            },
            "module_updated",
            ["12:34:56:3c:63:b2", "12:34:56:00:01:34:64:98"],
        ),
        (
            {
                "change": "module_assigned_to_room",
                "home_id": "91763b24c43d3e344f424e8b",
                "module_id": "12:34:56:00:01:34:64:98",
                "device_id": "12:34:56:3c:63:b2",
                "room_id": "2313121935",
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": "12:34:56:00:01:34:64:98",
                            "bridge": "12:34:56:3c:63:b2",
                            "room": "2313121935",
                        },
                    ],
                },
                "push_type": "topology_changed",
            },
            "module_assigned_to_room",
            ["12:34:56:3c:63:b2", "12:34:56:00:01:34:64:98"],
        ),
        (
            {
                "change": "device_updated",
                "device_id": "12:34:56:3c:63:b2",
                "home_id": "91763b24c43d3e344f424e8b",
                "home": {
                    "id": "91763b24c43d3e344f424e8b",
                    "modules": [
                        {
                            "id": "12:34:56:00:01:2b:02:46",
                            "bridge": "12:34:56:3c:63:b2",
                        },
                    ],
                },
                "push_type": "topology_changed",
            },
            "device_updated",
            ["12:34:56:3c:63:b2"],
        ),
    ],
)
async def test_process_webhook_topology_changed_variants(
    async_account,
    payload,
    expected_change,
    expected_touched,
):
    """Covers the three observed `change` variants; real captures, redacted."""
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.TOPOLOGY_DIRTY
    assert result.needs_refresh is True
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})
    assert result.event_type == expected_change
    assert result.touched_ids == expected_touched
    assert result.events == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_topology_changed_does_not_merge_modules(async_account):
    """Partial `home.modules[]` is not applied; a full refresh is authoritative."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    module_count_before = len(home.modules)
    known_module_id = "12:34:56:00:01:ae"  # NATherm1, in fixture
    assert known_module_id in home.modules

    payload = {
        "change": "module_updated",
        "device_id": "12:34:56:3c:63:b2",
        "module_id": "12:34:56:00:01:34:64:98",
        "home": {
            "id": home_id,
            "modules": [
                {
                    "id": "12:34:56:00:01:34:64:98",
                    "bridge": "12:34:56:3c:63:b2",
                    "name": "Mobile outlet 1",
                },
            ],
        },
        "push_type": "topology_changed",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.TOPOLOGY_DIRTY
    assert len(home.modules) == module_count_before
    assert "12:34:56:00:01:34:64:98" not in home.modules
    assert known_module_id in home.modules


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
    # No usable persons[] -> falls back to a single event, person_id unset.
    assert len(result.events) == 1
    assert result.events[0].person_id is None


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
    assert camera.floodlight == "auto"

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
    # The camera resolved fine, only its sub_type was malformed -- not a
    # stale topology, so no TOPOLOGY refresh.
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_non_str_therm_mode_keeps_model_clean(async_account):
    """A malformed therm_mode must not land on the home's therm_mode attribute."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    assert home.therm_mode == "schedule"

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
    # home is known, so therm_mode always resolves to a status poll (S1).
    assert result.refresh_scope == frozenset({RefreshScope.STATUS})


async def test_process_webhook_person_ids_are_strings(async_account):
    """Fan-out is per raw person entry, not a filtered list of valid ids."""
    result = await process_webhook(
        async_account,
        {
            "event_type": "person",
            "push_type": "NACamera-person",
            "home_id": "91763b24c43d3e344f424e8b",
            "persons": [{"id": 7}, {"id": None}, "junk", {"id": "p1"}],
        },
    )

    assert len(result.events) == 3
    assert [event.person_id for event in result.events] == [None, None, "p1"]


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
    assert room.therm_setpoint_mode == "away"
    assert room.therm_setpoint_temperature == 12

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
    assert room.therm_setpoint_mode == "away"

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
    # The room resolved fine, it just had nothing to merge -- not a stale
    # topology, so no TOPOLOGY refresh.
    assert result.refresh_scope == frozenset()


def test_room_setpoint_keys_match_room_annotations():
    """Pins `_ROOM_SETPOINT_KEYS` coercers to `Room`'s declared types."""
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
    """A suspension would yield instead of raising `StopIteration`."""
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


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_modules_merges_dimmer(async_account):
    """Real capture, remapped to the fixture's NLF dimmer."""
    home_id = "91763b24c43d3e344f424e8b"
    module_id = "00:11:22:33:00:11:45:fe"
    dimmer = async_account.homes[home_id].modules[module_id]
    assert dimmer.on is False
    assert dimmer.brightness == 63

    payload = {
        "extra_params": {
            "correlation_id": 13915705160800893000,
            "modules": [
                {
                    "brightness": 33,
                    "on": True,
                    "power": 0,
                    "reachable": True,
                    "room_id": "2313121935",
                    "id": module_id,
                    "type": "NLF",
                },
            ],
            "sequence_id": 12675,
            "source": "netcom",
        },
        "push_type": "device_event",
        "device_id": "12:34:56:3c:63:b2",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == [module_id]
    assert dimmer.on is True
    assert dimmer.brightness == 33
    assert len(result.events) == 1
    assert result.events[0].event_type is None
    assert result.events[0].module_id == module_id
    # Every module in the payload was merged -- no self-heal needed.
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_modules_unknown_module_self_heals(
    async_account,
):
    """A module id that isn't in the home self-heals with TOPOLOGY (S4)."""
    home_id = "91763b24c43d3e344f424e8b"

    payload = {
        "extra_params": {
            "modules": [{"id": "does-not-exist", "on": True}],
        },
        "push_type": "device_event",
        "device_id": "12:34:56:3c:63:b2",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_modules_mixed_known_and_unknown(
    async_account,
):
    """One known module merges; one unknown id still self-heals with TOPOLOGY."""
    home_id = "91763b24c43d3e344f424e8b"
    module_id = "00:11:22:33:00:11:45:fe"
    dimmer = async_account.homes[home_id].modules[module_id]
    assert dimmer.on is False
    assert dimmer.brightness == 63

    payload = {
        "extra_params": {
            "modules": [
                {"id": module_id, "on": True, "brightness": 33},
                {"id": "does-not-exist", "on": True},
            ],
        },
        "push_type": "device_event",
        "device_id": "12:34:56:3c:63:b2",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == [module_id]
    assert dimmer.on is True
    assert dimmer.brightness == 33
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_normalizes_weather_keys(async_account):
    """Real capture, redacted: weather keys renamed to model attrs before merge."""
    home_id = "91763b24c43d3e344f424e8b"
    main_id = "12:34:56:80:bb:26"
    child_id = "12:34:56:80:1c:42"
    main = async_account.homes[home_id].modules[main_id]
    child = async_account.homes[home_id].modules[child_id]
    assert main.wifi_strength == 45

    payload = {
        "extra_params": {
            "modules": [
                {
                    "id": main_id,
                    "wifi_status": 66,
                    "pressure_sea": 1015.3,
                    "pressure_abs": 1011.4,
                    "noise_current": 43,
                    "temperature": 22,
                    "co2": 381,
                    "humidity": 51,
                    "trend_temperature": "stable",
                    "firmware": 300,
                },
                {
                    "id": child_id,
                    "temperature": 22,
                    "humidity": 52,
                    "rf_status": 5,
                    "battery_vp": 5960,
                },
            ],
        },
        "push_type": "device_event",
        "device_id": main_id,
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert main_id in result.touched_ids
    assert child_id in result.touched_ids
    assert main.wifi_strength == 66
    assert main.pressure == 1015.3
    assert main.absolute_pressure == 1011.4
    assert main.noise == 43
    assert main.temperature == 22
    assert main.co2 == 381
    assert child.rf_strength == 5
    assert child.temperature == 22


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_modules_skips_camera(async_account):
    """Camera modules must never be merged (network I/O guard)."""
    home_id = "91763b24c43d3e344f424e8b"
    camera_id = "12:34:56:00:f1:62"  # NACamera, in fixture

    payload = {
        "extra_params": {
            "modules": [{"id": camera_id, "type": "NACamera", "monitoring": "off"}],
        },
        "push_type": "device_event",
        "device_id": "12:34:56:3c:63:b2",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    # The camera is present in the home, just deliberately skipped -- not a
    # missing entity, so no topology self-heal.
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_setpoint_event_merges_measured_temperature(
    async_account,
):
    """Real capture, remapped: touched_ids is the room, not the NAPlug relay (S7)."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_measured_temperature == 19.8
    assert room.therm_setpoint_mode == "away"
    assert room.therm_setpoint_temperature == 12

    payload = {
        "extra_params": {
            "device_type": "NAPlug",
            "event_type": "setpoint_event",
            "mode": "home",
            "room_id": "2746182631",
            "temperature": 16,
            "therm_measured_temperature": 23.3,
            "ts": 1786428073,
            "ts_begin": 0,
            "ts_end": 0,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == ["2746182631"]
    assert room.therm_measured_temperature == 23.3
    # setpoint not applied; only display_change is authoritative for that
    assert room.therm_setpoint_mode == "away"
    assert room.therm_setpoint_temperature == 12
    assert len(result.events) == 1
    assert result.events[0].event_type == "setpoint_event"
    assert result.events[0].mode == "home"
    assert result.refresh_scope == frozenset()


async def test_process_webhook_device_event_unknown_home_no_mutation(async_account):
    payload = {
        "extra_params": {
            "modules": [{"id": "00:11:22:33:00:11:45:fe", "on": True}],
        },
        "push_type": "device_event",
        "device_id": "12:34:56:3c:63:b2",
        "home_id": "does-not-exist",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


async def test_process_webhook_device_event_empty_extra_params(async_account):
    payload = {
        "extra_params": {},
        "push_type": "device_event",
        "home_id": "91763b24c43d3e344f424e8b",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.UNKNOWN
    assert result.refresh_scope == frozenset()
    assert result.events == []


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_temperature_variation_merges_room(
    async_account,
):
    """Real capture, remapped; keyed under `temperature`, not `therm_measured_temperature`."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2746182631"]
    assert room.therm_measured_temperature == 19.8

    payload = {
        "extra_params": {
            "device_type": "NAPlug",
            "event_type": "temperature_variation_event",
            "mode": "home",
            "room_id": "2746182631",
            "setpoint": 19,
            "temperature": 23.5,
            "ts": 1786426877,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == ["2746182631"]
    assert room.therm_measured_temperature == 23.5
    assert len(result.events) == 1
    assert result.events[0].event_type == "temperature_variation_event"
    assert result.events[0].mode == "home"
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_motor_data_event_merges_position(
    async_account,
):
    """Real capture, remapped: current_position merges onto the fixture's NBR cover."""
    home_id = "91763b24c43d3e344f424e8b"
    module_id = "0009999992"
    cover = async_account.homes[home_id].modules[module_id]
    assert cover.current_position == 0

    payload = {
        "extra_params": {
            "event_type": "motor_data_event",
            "module_id": module_id,
            "current_position": 2229,
            "motor_cmd": 0,
            "device_type": "NAPlug",
            "ts": 1786426877,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == [module_id]
    assert cover.current_position == 2229
    assert len(result.events) == 1
    assert result.events[0].event_type == "motor_data_event"
    assert result.events[0].module_id == module_id
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_heating_power_request_merges_room(
    async_account,
):
    """Real capture: heating demand % merges onto the room, drives HVAC action."""
    home_id = "91763b24c43d3e344f424e8b"
    room = async_account.homes[home_id].rooms["2940411577"]
    assert room.heating_power_request == 0

    payload = {
        "extra_params": {
            "device_type": "NAPlug",
            "event_type": "heating_power_request_event",
            "heating_power_request": 100,
            "room_id": "2940411577",
            "ts": 1786522899,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == ["2940411577"]
    assert room.heating_power_request == 100
    assert len(result.events) == 1
    assert result.events[0].event_type == "heating_power_request_event"
    assert result.refresh_scope == frozenset()


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_heating_power_request_unknown_room(
    async_account,
):
    """An unknown room_id self-heals with TOPOLOGY."""
    payload = {
        "extra_params": {
            "device_type": "NAPlug",
            "event_type": "heating_power_request_event",
            "heating_power_request": 100,
            "room_id": "does-not-exist",
            "ts": 1786522899,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": "91763b24c43d3e344f424e8b",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_temperature_variation_unknown_room(
    async_account,
):
    """A room_id that isn't in the home self-heals with TOPOLOGY (S4)."""
    payload = {
        "extra_params": {
            "device_type": "NAPlug",
            "event_type": "temperature_variation_event",
            "mode": "home",
            "room_id": "does-not-exist",
            "setpoint": 19,
            "temperature": 23.5,
            "ts": 1786426877,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": "91763b24c43d3e344f424e8b",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


async def test_process_webhook_device_event_motor_data_event_unknown_module(
    async_account,
):
    """An unresolvable module_id: no crash, touched_ids empty, event still surfaced."""
    payload = {
        "extra_params": {
            "event_type": "motor_data_event",
            "module_id": "does-not-exist",
            "current_position": 2229,
            "motor_cmd": 0,
            "device_type": "NAPlug",
            "ts": 1786426877,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": "91763b24c43d3e344f424e8b",
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert result.touched_ids == []
    assert len(result.events) == 1
    assert result.events[0].event_type == "motor_data_event"
    assert result.events[0].module_id == "does-not-exist"
    assert result.refresh_scope == frozenset({RefreshScope.TOPOLOGY})


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_device_event_boiler_event_surfaces_status(
    async_account,
):
    """Real capture, remapped: boiler_status surfaces on the event regardless of merge.

    The fixture has four boiler_status modules and none is bridged to the
    (remapped) device_id, so the merge is ambiguous and skipped.
    """
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]
    natherm1 = home.modules["12:34:56:00:01:ae"]
    oth = home.modules["12:34:56:20:f5:44"]
    natherm1_before = natherm1.boiler_status
    oth_before = oth.boiler_status

    payload = {
        "extra_params": {
            "event_type": "boiler_event",
            "boiler_status": "boiler_on",
            "device_type": "NAPlug",
            "ts": 1786426877,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.STATE
    assert len(result.events) == 1
    assert result.events[0].event_type == "boiler_event"
    assert result.events[0].boiler_status is True
    assert natherm1.boiler_status == natherm1_before
    assert oth.boiler_status == oth_before
    assert result.touched_ids == ["12:34:56:00:bc:24"]
    # Ambiguous skip is expected, not a missing entity -- never self-heals.
    assert result.refresh_scope == frozenset()


async def test_process_webhook_device_event_boiler_off_maps_false(async_account):
    """boiler_off maps to False on the surfaced event."""
    payload = {
        "extra_params": {
            "event_type": "boiler_event",
            "boiler_status": "boiler_off",
            "device_type": "NAPlug",
            "ts": 1786426877,
        },
        "push_type": "device_event",
        "device_id": "12:34:56:00:bc:24",
        "home_id": "91763b24c43d3e344f424e8b",
    }
    result = await process_webhook(async_account, payload)

    assert result.events[0].boiler_status is False


async def test_process_webhook_device_event_diagnosis_event_surfaces(async_account):
    """Real capture, redacted: `type`-keyed device_event surfaces as EVENT, no merge."""
    home_id = "91763b24c43d3e344f424e8b"
    module_count_before = len(async_account.homes[home_id].modules)

    payload = {
        "extra_params": {
            "type": "diagnosis_event",
            "diagnosis_content": {
                "modules": [
                    {
                        "firmware_revision": 62,
                        "id": "12:34:56:00:01:34:64:98",
                        "type": "NLPM",
                    },
                ],
                "type": "ota_limit_reached",
            },
        },
        "push_type": "device_event",
        "device_id": "12:34:56:3c:63:b2",
        "home_id": home_id,
    }
    result = await process_webhook(async_account, payload)

    assert result.kind is WebhookKind.EVENT
    assert len(result.events) == 1
    assert result.events[0].event_type == "diagnosis_event"
    assert result.touched_ids == ["12:34:56:3c:63:b2"]
    assert result.refresh_scope == frozenset()
    assert len(async_account.homes[home_id].modules) == module_count_before


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_records_delivery_time(async_account):
    """Any processed payload records when it arrived."""
    assert async_account.last_webhook_at is None

    await process_webhook(async_account, {"push_type": "webhook_activation"})

    assert async_account.last_webhook_at is not None


@pytest.mark.usefixtures("async_home")
async def test_process_webhook_records_delivery_time_for_unknown_payloads(
    async_account,
):
    """An unrecognised payload still proves the webhook path is delivering."""
    await process_webhook(async_account, {"push_type": "display_change"})

    assert async_account.last_webhook_at is not None


async def test_last_webhook_at_records_an_unclassifiable_payload(async_account):
    """Delivery of anything proves the path works, even if nothing parses.

    The stamp is the first statement of process_webhook for this reason:
    a payload with no event_type and no push_type returns UNKNOWN through an
    early return, and must still count as a delivery.
    """
    before = time()

    result = await process_webhook(async_account, {})

    assert result.kind is WebhookKind.UNKNOWN
    assert async_account.last_webhook_at is not None
    assert async_account.last_webhook_at >= before


async def test_last_webhook_at_is_wall_clock(async_account):
    """Consumers compute an age from it, so it must be comparable to time()."""
    await async_account.process_webhook({"push_type": "webhook_activation"})

    assert async_account.last_webhook_at == pytest.approx(time(), abs=5)
