"""Support for processing Netatmo webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import logging
from time import time
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from pyatmo.event import EventTypes
from pyatmo.helpers import dict_entries, number_or_none, str_or_none
from pyatmo.modules.device_types import DeviceCategory

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyatmo.account import AsyncAccount
    from pyatmo.home import Home
    from pyatmo.modules.module import (
        BoilerMixin,
        FloodlightMixin,
        MonitoringMixin,
        ShutterMixin,
    )
    from pyatmo.room import Room

LOG: logging.Logger = logging.getLogger(__name__)

EVENT_TYPE_ON = "on"
EVENT_TYPE_OFF = "off"
EVENT_TYPE_LIGHT_MODE = "light_mode"
EVENT_TYPE_SET_POINT = "set_point"
EVENT_TYPE_CANCEL_SET_POINT = "cancel_set_point"
EVENT_TYPE_SETPOINT_EVENT = "setpoint_event"
EVENT_TYPE_THERM_MODE = "therm_mode"
EVENT_TYPE_SCHEDULE = "schedule"
EVENT_TYPE_TEMPERATURE_VARIATION_EVENT = "temperature_variation_event"
EVENT_TYPE_MOTOR_DATA_EVENT = "motor_data_event"
EVENT_TYPE_BOILER_EVENT = "boiler_event"
EVENT_TYPE_HEATING_POWER_REQUEST_EVENT = "heating_power_request_event"

# device_event energy `event_type`s with a known merge; anything else with a
# resolved type (e.g. diagnosis_event) is surfaced as an EVENT, unmerged.
_DEVICE_ENERGY_EVENT_TYPES = frozenset(
    {
        EVENT_TYPE_TEMPERATURE_VARIATION_EVENT,
        EVENT_TYPE_SETPOINT_EVENT,
        EVENT_TYPE_MOTOR_DATA_EVENT,
        EVENT_TYPE_BOILER_EVENT,
        EVENT_TYPE_HEATING_POWER_REQUEST_EVENT,
    },
)

WEBHOOK_ACTIVATION = "webhook_activation"
WEBHOOK_DEACTIVATION = "webhook_deactivation"
WEBHOOK_DEVICE_EVENT = "device_event"
WEBHOOK_TOPOLOGY_CHANGED = "topology_changed"
CAMERA_CONNECTION_WEBHOOKS = frozenset(
    {"NACamera-connection", "NOC-connection", "NDB-connection", "NPC-connection"},
)

STATE_EVENT_TYPES = frozenset(
    {
        EVENT_TYPE_ON,
        EVENT_TYPE_OFF,
        EVENT_TYPE_LIGHT_MODE,
        EVENT_TYPE_SET_POINT,
        EVENT_TYPE_CANCEL_SET_POINT,
        EVENT_TYPE_SETPOINT_EVENT,
        EVENT_TYPE_THERM_MODE,
    },
)

_ROOM_SETPOINT_KEYS: dict[str, Callable[[Any], Any]] = {
    "therm_setpoint_mode": str_or_none,
    "therm_setpoint_fp": str_or_none,
    "therm_setpoint_temperature": number_or_none,
    "therm_setpoint_start_time": number_or_none,
    "therm_setpoint_end_time": number_or_none,
    "cooling_setpoint_mode": str_or_none,
    "cooling_setpoint_temperature": number_or_none,
    "cooling_setpoint_start_time": number_or_none,
    "cooling_setpoint_end_time": number_or_none,
}

_DEVICE_EVENT_ATTRIBUTE_MAP: dict[str, str] = {
    "wifi_status": "wifi_strength",
    "rf_status": "rf_strength",
    "firmware": "firmware_revision",
    "pressure_sea": "pressure",
    "pressure_abs": "absolute_pressure",
    "noise_current": "noise",
    "trend_temperature": "temp_trend",
}

_EXTRA_EVENT_TYPES = frozenset(
    {
        "human",
        "animal",
        "vehicle",
        "alarm_started",
    },
)

EVENT_EVENT_TYPES = (
    frozenset(event_type.value for event_type in EventTypes) | _EXTRA_EVENT_TYPES
) - STATE_EVENT_TYPES


class WebhookKind(Enum):
    """Category a webhook payload was routed to."""

    STATE = "state"
    EVENT = "event"
    TOPOLOGY_DIRTY = "topology_dirty"
    LIFECYCLE = "lifecycle"
    UNKNOWN = "unknown"


class LifecycleStatus(Enum):
    """Lifecycle status for LIFECYCLE-kind payloads."""

    ACTIVATION = "activation"
    DEACTIVATION = "deactivation"
    CONNECTION = "connection"
    DISCONNECTION = "disconnection"


class RefreshScope(Enum):
    """Which poll a consumer should run to reconcile after a webhook."""

    TOPOLOGY = "topology"
    STATUS = "status"


@dataclass(frozen=True)
class WebhookEvent:
    """A parsed webhook event (distinct from the /getevents Event stream)."""

    event_type: str | None
    push_type: str | None
    home_id: str | None
    module_id: str | None = None
    camera_id: str | None = None
    device_id: str | None = None
    room_id: str | None = None
    mode: str | None = None
    boiler_status: bool | None = None
    person_id: str | None = None
    person_name: str | None = None
    is_known: bool | None = None
    face_url: str | None = None
    sub_type: str | None = None
    snapshot_url: str | None = None
    vignette_url: str | None = None
    event_id: str | None = None
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookResult:
    """Outcome of processing one webhook payload."""

    home_id: str | None
    event_type: str | None
    push_type: str | None
    kind: WebhookKind
    touched_ids: list[str] = field(default_factory=list)
    events: list[WebhookEvent] = field(default_factory=list)
    refresh_scope: frozenset[RefreshScope] = frozenset()
    lifecycle: LifecycleStatus | None = None

    @property
    def needs_refresh(self) -> bool:
        """True when the consumer should poll; see `refresh_scope` for which."""
        return bool(self.refresh_scope)


def classify(event_type: str | None, push_type: str | None) -> WebhookKind:
    """Route a webhook payload to a WebhookKind by event_type/push_type."""
    if push_type in (WEBHOOK_ACTIVATION, WEBHOOK_DEACTIVATION):
        return WebhookKind.LIFECYCLE
    if (
        push_type in CAMERA_CONNECTION_WEBHOOKS
        or event_type == "connection"
        or _is_disconnection(event_type, push_type)
    ):
        return WebhookKind.LIFECYCLE
    if event_type in STATE_EVENT_TYPES:
        return WebhookKind.STATE
    if event_type == EVENT_TYPE_SCHEDULE:
        return WebhookKind.TOPOLOGY_DIRTY
    if event_type in EVENT_EVENT_TYPES:
        return WebhookKind.EVENT
    return WebhookKind.UNKNOWN


def resolve_home_id(payload: dict[str, Any]) -> str | None:
    """Return the home id from either the top-level or nested `home` block."""
    home = payload.get("home")
    nested = str_or_none(home.get("id")) if isinstance(home, dict) else None
    return str_or_none(payload.get("home_id")) or nested


def _extra_params(payload: dict[str, Any]) -> dict[str, Any]:
    extra = payload.get("extra_params")
    return extra if isinstance(extra, dict) else {}


def _bool_or_none(value: Any) -> bool | None:  # noqa: ANN401
    return value if isinstance(value, bool) else None


def _map_boiler_status(raw: Any) -> bool | None:  # noqa: ANN401
    if raw == "boiler_on":
        return True
    if raw == "boiler_off":
        return False
    return None


def _resolve_person_name(home: Home | None, person_id: str | None) -> str | None:
    if home is None or person_id is None:
        return None
    person = home.persons.get(person_id)
    return getattr(person, "pseudo", None)


def _shared_event_fields(
    payload: dict[str, Any],
    extra: dict[str, Any],
    home_id: str | None,
    push_type: str | None,
    event_type: str | None,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "push_type": push_type,
        "home_id": home_id,
        "module_id": str_or_none(payload.get("module_id"))
        or str_or_none(extra.get("module_id")),
        "camera_id": str_or_none(payload.get("camera_id")),
        "device_id": str_or_none(payload.get("device_id")),
        "room_id": str_or_none(payload.get("room_id"))
        or str_or_none(extra.get("room_id")),
        "mode": str_or_none(payload.get("mode")) or str_or_none(extra.get("mode")),
        "boiler_status": _map_boiler_status(extra.get("boiler_status")),
        "sub_type": str_or_none(payload.get("sub_type")),
        "snapshot_url": str_or_none(payload.get("snapshot_url")),
        "vignette_url": str_or_none(payload.get("vignette_url")),
        "event_id": str_or_none(payload.get("event_id")),
        "message": str_or_none(payload.get("message")),
        "raw": payload,
    }


def _build_person_event(
    payload: dict[str, Any],
    extra: dict[str, Any],
    person: dict[str, Any],
    *,
    home: Home | None,
    home_id: str | None,
    push_type: str | None,
) -> WebhookEvent:
    person_id = str_or_none(person.get("id"))
    return WebhookEvent(
        **_shared_event_fields(payload, extra, home_id, push_type, "person"),
        person_id=person_id,
        is_known=_bool_or_none(person.get("is_known")),
        face_url=str_or_none(person.get("face_url")),
        person_name=_resolve_person_name(home, person_id),
    )


def build_webhook_events(
    payload: dict[str, Any],
    home: Home | None,
) -> list[WebhookEvent]:
    """Build the WebhookEvent(s) a payload carries, regardless of `kind`."""
    extra = _extra_params(payload)
    home_id = resolve_home_id(payload)
    push_type = str_or_none(payload.get("push_type"))

    modules = dict_entries(extra.get("modules"))
    if modules:
        device_id = str_or_none(payload.get("device_id"))
        return [
            WebhookEvent(
                event_type=None,
                push_type=push_type,
                home_id=home_id,
                module_id=str_or_none(module.get("id")),
                room_id=str_or_none(module.get("room_id")),
                device_id=device_id,
                raw=payload,
            )
            for module in modules
        ]

    event_type = (
        str_or_none(payload.get("event_type"))
        or str_or_none(extra.get("event_type"))
        or str_or_none(extra.get("type"))
    )
    if event_type is None:
        return []

    if event_type == "person":
        persons = dict_entries(payload.get("persons"))
        if persons:
            return [
                _build_person_event(
                    payload,
                    extra,
                    person,
                    home=home,
                    home_id=home_id,
                    push_type=push_type,
                )
                for person in persons
            ]

    return [
        WebhookEvent(
            **_shared_event_fields(payload, extra, home_id, push_type, event_type),
        ),
    ]


async def process_webhook(
    account: AsyncAccount,
    payload: dict[str, Any],
) -> WebhookResult:
    """Parse, normalize, and merge a Netatmo webhook payload."""
    # Delivery of anything, including a payload this library cannot classify,
    # proves the webhook path works end to end.
    account.last_webhook_at = time()

    event_type = str_or_none(payload.get("event_type"))
    push_type = str_or_none(payload.get("push_type"))
    home_id = resolve_home_id(payload)

    if not event_type and not push_type:
        LOG.debug("Webhook payload without event_type/push_type: %s", payload)
        return WebhookResult(home_id, event_type, push_type, WebhookKind.UNKNOWN)

    # No await here except device_event's module merge -- never suspend on the webhook response path.
    if push_type == WEBHOOK_DEVICE_EVENT:
        result = await _process_device_event(account, payload)
    elif push_type == WEBHOOK_TOPOLOGY_CHANGED:
        result = _process_topology_changed(home_id, payload)
    else:
        result = _process_standard_envelope(
            account,
            home_id,
            event_type,
            push_type,
            payload,
        )

    home = account.homes.get(home_id) if home_id else None
    return replace(result, events=build_webhook_events(payload, home))


def _process_standard_envelope(
    account: AsyncAccount,
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    kind = classify(event_type, push_type)

    if kind is WebhookKind.LIFECYCLE:
        return _process_lifecycle(account, home_id, event_type, push_type, payload)

    if kind is WebhookKind.STATE:
        return _process_state(account, home_id, event_type, push_type, payload)

    if kind is WebhookKind.EVENT:
        return _process_event(home_id, event_type, push_type, payload)

    if kind is WebhookKind.TOPOLOGY_DIRTY:
        return WebhookResult(
            home_id,
            event_type,
            push_type,
            WebhookKind.TOPOLOGY_DIRTY,
            refresh_scope=frozenset({RefreshScope.TOPOLOGY, RefreshScope.STATUS}),
        )

    LOG.debug(
        "Unrecognized webhook (event_type=%s, push_type=%s)", event_type, push_type
    )
    return WebhookResult(home_id, event_type, push_type, WebhookKind.UNKNOWN)


class MergeOutcome(NamedTuple):
    """Result of a best-effort model merge.

    `unresolved` is True only when the payload named an entity that is not
    loaded in the home -- a missing entity worth a topology re-fetch. A
    deliberately skipped (camera) or ambiguous (no `module_id`) target leaves
    it False.
    """

    touched: list[str]
    unresolved: bool


def _topology_if_unresolved(unresolved: bool) -> frozenset[RefreshScope]:
    """Map a missing-entity flag to a topology re-fetch, else no refresh."""
    return frozenset({RefreshScope.TOPOLOGY}) if unresolved else frozenset()


async def _process_device_event(
    account: AsyncAccount,
    payload: dict[str, Any],
) -> WebhookResult:
    extra = _extra_params(payload)
    home_id = resolve_home_id(payload)
    modules = dict_entries(extra.get("modules"))

    if modules:
        touched, unresolved = await _merge_device_modules(account, home_id, modules)
        # A module id named in the payload but not present in the home (not
        # merely skipped, e.g. a camera) means the consumer should re-fetch
        # topology.
        refresh_scope = _topology_if_unresolved(unresolved)
        return WebhookResult(
            home_id,
            str_or_none(extra.get("event_type")),
            WEBHOOK_DEVICE_EVENT,
            WebhookKind.STATE,
            touched_ids=touched,
            refresh_scope=refresh_scope,
        )

    event_type = str_or_none(extra.get("event_type")) or str_or_none(extra.get("type"))

    if event_type in _DEVICE_ENERGY_EVENT_TYPES:
        touched, unresolved = _merge_device_energy_event(
            account,
            home_id,
            payload,
            event_type,
            extra,
        )
        refresh_scope = _topology_if_unresolved(unresolved)
        return WebhookResult(
            home_id,
            event_type,
            WEBHOOK_DEVICE_EVENT,
            WebhookKind.STATE,
            touched_ids=touched,
            refresh_scope=refresh_scope,
        )

    if event_type is not None:
        # Unrecognized device-event type (e.g. diagnosis_event): no known
        # merge target, surface it as an EVENT instead of dropping it.
        device_id = str_or_none(payload.get("device_id"))
        return WebhookResult(
            home_id,
            event_type,
            WEBHOOK_DEVICE_EVENT,
            WebhookKind.EVENT,
            touched_ids=[device_id] if device_id else [],
        )

    return WebhookResult(home_id, None, WEBHOOK_DEVICE_EVENT, WebhookKind.UNKNOWN)


def _merge_device_energy_event(
    account: AsyncAccount,
    home_id: str | None,
    payload: dict[str, Any],
    event_type: str,
    extra: dict[str, Any],
) -> MergeOutcome:
    """Dispatch an energy device_event to its room/module merge.

    `boiler_event` never reports unresolved: an ambiguous skip (no bridge
    match, more than one candidate) is expected, not a missing entity.
    """
    if event_type == EVENT_TYPE_MOTOR_DATA_EVENT:
        return _merge_motor_data_event(account, home_id, extra)
    if event_type == EVENT_TYPE_BOILER_EVENT:
        return MergeOutcome(
            _merge_boiler_event(account, home_id, payload, extra), False
        )
    if event_type == EVENT_TYPE_HEATING_POWER_REQUEST_EVENT:
        return _merge_heating_power_request_event(account, home_id, extra)
    # setpoint_event / temperature_variation_event -- room telemetry merge.
    # Setpoints stay authoritative via display_change; never merged here.
    return _merge_device_energy_temperature(account, home_id, event_type, extra)


def _merge_motor_data_event(
    account: AsyncAccount,
    home_id: str | None,
    extra: dict[str, Any],
) -> MergeOutcome:
    module_id = str_or_none(extra.get("module_id"))
    if not module_id:
        return MergeOutcome([], False)
    home = account.homes.get(home_id) if home_id else None
    module = home.modules.get(module_id) if home is not None else None
    if module is None:
        return MergeOutcome([], True)
    position = number_or_none(extra.get("current_position"))
    if position is None or not hasattr(module, "current_position"):
        return MergeOutcome([], False)
    cast("ShutterMixin", module).current_position = int(position)
    return MergeOutcome([module_id], False)


def _merge_boiler_event(
    account: AsyncAccount,
    home_id: str | None,
    payload: dict[str, Any],
    extra: dict[str, Any],
) -> list[str]:
    device_id = str_or_none(payload.get("device_id"))
    fallback = [device_id] if device_id else []

    mapped = _map_boiler_status(extra.get("boiler_status"))
    home = account.homes.get(home_id) if home_id else None
    if mapped is None or home is None:
        return fallback

    boiler_modules = [
        module for module in home.modules.values() if hasattr(module, "boiler_status")
    ]
    target = next(
        (m for m in boiler_modules if getattr(m, "bridge", None) == device_id),
        None,
    )
    if target is None and len(boiler_modules) == 1:
        target = boiler_modules[0]
    if target is None:
        return fallback

    cast("BoilerMixin", target).boiler_status = mapped
    return [target.entity_id]


def _merge_heating_power_request_event(
    account: AsyncAccount,
    home_id: str | None,
    extra: dict[str, Any],
) -> MergeOutcome:
    room_id = str_or_none(extra.get("room_id"))
    if not room_id:
        return MergeOutcome([], False)
    home = account.homes.get(home_id) if home_id else None
    room = home.rooms.get(room_id) if home is not None else None
    if room is None:
        return MergeOutcome([], True)
    request = number_or_none(extra.get("heating_power_request"))
    if request is None:
        return MergeOutcome([], False)
    room.heating_power_request = int(request)
    return MergeOutcome([room.entity_id], False)


def _device_event_measured_temperature(
    event_type: str,
    extra: dict[str, Any],
) -> float | None:
    if event_type == EVENT_TYPE_TEMPERATURE_VARIATION_EVENT:
        return number_or_none(extra.get("temperature"))
    if event_type == EVENT_TYPE_SETPOINT_EVENT:
        return number_or_none(extra.get("therm_measured_temperature"))
    return None


def _merge_device_energy_temperature(
    account: AsyncAccount,
    home_id: str | None,
    event_type: str,
    extra: dict[str, Any],
) -> MergeOutcome:
    room_id = str_or_none(extra.get("room_id"))
    if not room_id:
        return MergeOutcome([], False)
    home = account.homes.get(home_id) if home_id else None
    room = home.rooms.get(room_id) if home is not None else None
    if room is None:
        return MergeOutcome([], True)
    measured = _device_event_measured_temperature(event_type, extra)
    if measured is None:
        return MergeOutcome([], False)
    room.therm_measured_temperature = measured
    return MergeOutcome([room.entity_id], False)


def _normalize_device_event_module(module_data: dict[str, Any]) -> dict[str, Any]:
    return {_DEVICE_EVENT_ATTRIBUTE_MAP.get(k, k): v for k, v in module_data.items()}


async def _merge_device_modules(
    account: AsyncAccount,
    home_id: str | None,
    modules: list[dict[str, Any]],
) -> MergeOutcome:
    """Merge each device_event module's fields into the loaded model.

    A camera that is present but skipped (I/O guard) and an entry with a
    missing/non-string id both count as resolved: `unresolved` stays False
    for them. A malformed id is not a missing entity.
    """
    home = account.homes.get(home_id) if home_id else None
    touched: list[str] = []
    unresolved = False
    for module_data in modules:
        module_id = str_or_none(module_data.get("id"))
        if not module_id:
            continue
        module = home.modules.get(module_id) if home is not None else None
        if module is None:
            unresolved = True
            continue
        if getattr(module, "device_category", None) == DeviceCategory.camera:
            # Camera.update() does network I/O; never run that from a webhook.
            continue
        await module.update(_normalize_device_event_module(module_data))
        touched.append(module.entity_id)
    return MergeOutcome(touched, unresolved)


def _process_topology_changed(
    home_id: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    return WebhookResult(
        home_id,
        str_or_none(payload.get("change")),
        WEBHOOK_TOPOLOGY_CHANGED,
        WebhookKind.TOPOLOGY_DIRTY,
        touched_ids=_touched_from_payload(payload),
        refresh_scope=frozenset({RefreshScope.TOPOLOGY}),
    )


def _process_state(
    account: AsyncAccount,
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    home = account.homes.get(home_id) if home_id else None
    if home_id is None or home is None:
        LOG.debug("Webhook STATE payload for unknown home %s; skipping", home_id)
        return WebhookResult(
            home_id,
            event_type,
            push_type,
            WebhookKind.STATE,
            refresh_scope=frozenset({RefreshScope.TOPOLOGY}),
        )

    touched: list[str] = []
    refresh_scope: frozenset[RefreshScope] = frozenset()
    if event_type in (
        EVENT_TYPE_SET_POINT,
        EVENT_TYPE_CANCEL_SET_POINT,
        EVENT_TYPE_SETPOINT_EVENT,
    ):
        touched, unresolved = _merge_rooms(home, payload)
        refresh_scope = _topology_if_unresolved(not touched and unresolved)
    elif event_type == EVENT_TYPE_THERM_MODE:
        home_data = payload.get("home")
        therm_mode = (
            str_or_none(home_data.get("therm_mode"))
            if isinstance(home_data, dict)
            else None
        )
        if therm_mode is not None:
            home.therm_mode = therm_mode
            touched = [home_id]
        # therm_mode changes every room's effective setpoint server-side; home
        # is already known here, so this always resolves to a status poll.
        refresh_scope = frozenset({RefreshScope.STATUS})
    elif event_type in (EVENT_TYPE_ON, EVENT_TYPE_OFF):
        touched, unresolved = _merge_camera_monitoring(home, event_type, payload)
        refresh_scope = _topology_if_unresolved(not touched and unresolved)
    elif event_type == EVENT_TYPE_LIGHT_MODE:
        touched, unresolved = _merge_camera_floodlight(home, payload)
        refresh_scope = _topology_if_unresolved(not touched and unresolved)

    return WebhookResult(
        home_id,
        event_type,
        push_type,
        WebhookKind.STATE,
        touched_ids=touched,
        refresh_scope=refresh_scope,
    )


def _merge_rooms(home: Home, payload: dict[str, Any]) -> MergeOutcome:
    """Merge setpoint keys for each room named in the payload."""
    touched: list[str] = []
    unresolved = False
    home_data = payload.get("home")
    if not isinstance(home_data, dict):
        return MergeOutcome(touched, unresolved)
    for room in dict_entries(home_data.get("rooms")):
        room_id = str_or_none(room.get("id"))
        room_obj = home.rooms.get(room_id) if room_id else None
        if room_obj is None:
            if room_id:
                unresolved = True
            continue
        if _merge_room_setpoints(room_obj, room):
            touched.append(room_obj.entity_id)
    return MergeOutcome(touched, unresolved)


def _merge_room_setpoints(room_obj: Room, room: dict[str, Any]) -> bool:
    applied = False
    for key, coerce in _ROOM_SETPOINT_KEYS.items():
        if key not in room:
            continue
        raw = room[key]
        value = coerce(raw)
        if value is None and raw is not None:
            continue
        setattr(room_obj, key, value)
        applied = True
    return applied


def _camera_id(payload: dict[str, Any]) -> str | None:
    camera_id = str_or_none(payload.get("camera_id"))
    return camera_id or str_or_none(payload.get("device_id"))


def _merge_camera_monitoring(
    home: Home,
    event_type: str | None,
    payload: dict[str, Any],
) -> MergeOutcome:
    """Merge camera monitoring on/off state."""
    camera_id = _camera_id(payload)
    if not camera_id:
        return MergeOutcome([], False)
    module = home.modules.get(camera_id)
    if module is None:
        return MergeOutcome([], True)
    if not hasattr(module, "monitoring"):
        return MergeOutcome([], False)
    cast("MonitoringMixin", module).monitoring = event_type == EVENT_TYPE_ON
    return MergeOutcome([camera_id], False)


def _merge_camera_floodlight(
    home: Home,
    payload: dict[str, Any],
) -> MergeOutcome:
    """Merge camera floodlight (light_mode) state."""
    camera_id = _camera_id(payload)
    if not camera_id:
        return MergeOutcome([], False)
    module = home.modules.get(camera_id)
    if module is None:
        return MergeOutcome([], True)
    sub_type = str_or_none(payload.get("sub_type"))
    if sub_type is None or not hasattr(module, "floodlight"):
        return MergeOutcome([], False)
    cast("FloodlightMixin", module).floodlight = sub_type
    return MergeOutcome([camera_id], False)


def _touched_from_payload(payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("device_id", "camera_id", "module_id"):
        value = str_or_none(payload.get(key))
        if value and value not in ids:
            ids.append(value)
    return ids


def _process_event(
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    return WebhookResult(
        home_id,
        event_type,
        push_type,
        WebhookKind.EVENT,
        touched_ids=_touched_from_payload(payload),
    )


def _is_disconnection(event_type: str | None, push_type: str | None) -> bool:
    return (
        event_type == "disconnection"
        or push_type == "disconnection"
        or (push_type is not None and push_type.endswith("-disconnection"))
    )


_PUSH_LIFECYCLE: dict[str | None, LifecycleStatus] = {
    WEBHOOK_ACTIVATION: LifecycleStatus.ACTIVATION,
    WEBHOOK_DEACTIVATION: LifecycleStatus.DEACTIVATION,
}


def _process_lifecycle(
    account: AsyncAccount,
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    lifecycle = _PUSH_LIFECYCLE.get(push_type)
    if lifecycle is not None:
        return WebhookResult(
            home_id,
            event_type,
            push_type,
            WebhookKind.LIFECYCLE,
            lifecycle=lifecycle,
        )
    return _process_connectivity(account, home_id, event_type, push_type, payload)


def _process_connectivity(
    account: AsyncAccount,
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    """Merge camera reachability from a connection/disconnection webhook."""
    home = account.homes.get(home_id) if home_id else None
    camera_id = _camera_id(payload)
    module = home.modules.get(camera_id) if home is not None and camera_id else None
    touched = [camera_id] if camera_id and module is not None else []

    if _is_disconnection(event_type, push_type):
        if module is not None:
            module.mark_unreachable()
        return WebhookResult(
            home_id,
            event_type,
            push_type,
            WebhookKind.LIFECYCLE,
            touched_ids=touched,
            lifecycle=LifecycleStatus.DISCONNECTION,
        )

    if module is not None:
        module.mark_reachable()
    return WebhookResult(
        home_id,
        event_type,
        push_type,
        WebhookKind.LIFECYCLE,
        touched_ids=touched,
        refresh_scope=frozenset({RefreshScope.STATUS}),
        lifecycle=LifecycleStatus.CONNECTION,
    )
