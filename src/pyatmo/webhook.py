"""Support for processing Netatmo webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import TYPE_CHECKING, Any, cast

from pyatmo.event import EventTypes
from pyatmo.helpers import dict_entries, number_or_none, str_or_none
from pyatmo.modules.device_types import DeviceCategory

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyatmo.account import AsyncAccount
    from pyatmo.home import Home
    from pyatmo.modules.module import FloodlightMixin, MonitoringMixin
    from pyatmo.room import Room

LOG: logging.Logger = logging.getLogger(__name__)

EVENT_TYPE_ON = "on"
EVENT_TYPE_OFF = "off"
EVENT_TYPE_LIGHT_MODE = "light_mode"
EVENT_TYPE_SET_POINT = "set_point"
EVENT_TYPE_CANCEL_SET_POINT = "cancel_set_point"
# Real `display_change` payloads use this name instead of `set_point`; same
# nested `home.rooms[]` therm_setpoint_* keys, so it is treated as an alias.
EVENT_TYPE_SETPOINT_EVENT = "setpoint_event"
EVENT_TYPE_THERM_MODE = "therm_mode"
EVENT_TYPE_SCHEDULE = "schedule"

WEBHOOK_ACTIVATION = "webhook_activation"
WEBHOOK_DEACTIVATION = "webhook_deactivation"
# A second envelope format: no top-level event_type, real content nested in
# `extra_params`. Routed by `_process_device_event`, before `classify()`.
WEBHOOK_DEVICE_EVENT = "device_event"
CAMERA_CONNECTION_WEBHOOKS = frozenset(
    {"NACamera-connection", "NOC-connection", "NDB-connection"},
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


@dataclass(frozen=True)
class WebhookEvent:
    """A parsed webhook event (distinct from the /getevents Event stream).

    `frozen` prevents rebinding an attribute but not mutating one: `person_ids`
    and `raw` stay mutable, so instances are not hashable and `hash()` or set
    membership raises `TypeError`. Compare them by value instead.
    """

    event_type: str | None
    push_type: str | None
    home_id: str | None
    module_id: str | None = None
    camera_id: str | None = None
    device_id: str | None = None
    person_ids: list[str] = field(default_factory=list)
    sub_type: str | None = None
    snapshot_url: str | None = None
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookResult:
    """Outcome of processing one webhook payload.

    Not hashable, for the same reason as `WebhookEvent`: `touched_ids` and
    `events` stay mutable despite `frozen`. Compare by value instead.

    The `touched_ids` namespace depends on `event_type` -- room ids for
    set_point and cancel_set_point, the home id for therm_mode, module ids for
    on/off, light_mode and EVENT payloads.
    """

    home_id: str | None
    event_type: str | None
    push_type: str | None
    kind: WebhookKind
    touched_ids: list[str] = field(default_factory=list)
    events: list[WebhookEvent] = field(default_factory=list)
    needs_refresh: bool = False
    lifecycle: LifecycleStatus | None = None


def classify(event_type: str | None, push_type: str | None) -> WebhookKind:
    """Route a webhook payload to a WebhookKind by event_type/push_type."""
    if push_type in (WEBHOOK_ACTIVATION, WEBHOOK_DEACTIVATION):
        return WebhookKind.LIFECYCLE
    if push_type in CAMERA_CONNECTION_WEBHOOKS:
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
    """Return the `device_event` envelope's `extra_params` block, or `{}`.

    That envelope nests its real content here instead of at the top level;
    callers must tolerate a missing or malformed block without raising.
    """
    extra = payload.get("extra_params")
    return extra if isinstance(extra, dict) else {}


def build_webhook_event(payload: dict[str, Any]) -> WebhookEvent:
    """Build a WebhookEvent from an EVENT-class payload.

    `event_type` falls back to `extra_params.event_type` for the
    `device_event` envelope, which carries no top-level `event_type`.
    """
    return WebhookEvent(
        event_type=str_or_none(payload.get("event_type"))
        or str_or_none(_extra_params(payload).get("event_type")),
        push_type=str_or_none(payload.get("push_type")),
        home_id=resolve_home_id(payload),
        module_id=str_or_none(payload.get("module_id")),
        camera_id=str_or_none(payload.get("camera_id")),
        device_id=str_or_none(payload.get("device_id")),
        person_ids=[
            person_id
            for person in dict_entries(payload.get("persons"))
            if (person_id := str_or_none(person.get("id")))
        ],
        sub_type=str_or_none(payload.get("sub_type")),
        snapshot_url=str_or_none(payload.get("snapshot_url")),
        message=str_or_none(payload.get("message")),
        raw=payload,
    )


async def process_webhook(
    account: AsyncAccount,
    payload: dict[str, Any],
) -> WebhookResult:
    """Parse, normalize, and merge a Netatmo webhook payload.

    Performs no I/O and never suspends for the standard envelope, because
    Netatmo requires a webhook endpoint to answer immediately and deactivates
    one that does not. Do not add an `await` here: it would put network
    latency, including the 429 backoff in `auth.py`, on the response path. The
    `device_event` envelope is the one documented exception: its module merge
    goes through `Module.update`, which is `async` but performs no I/O of its
    own for the plain (non-Camera) modules it is used for today.

    Merging is therefore best-effort. An `async_update_*` call already in flight
    fetched its snapshot before this payload arrived, and will overwrite the
    merge when it completes; the next successful poll restores the true state,
    since the server is authoritative. Callers that need the merge to survive
    should answer the webhook first and then apply the result in a task ordered
    after any in-flight refresh -- `needs_refresh` schedules that follow-up.
    """
    event_type = str_or_none(payload.get("event_type"))
    push_type = str_or_none(payload.get("push_type"))
    home_id = resolve_home_id(payload)

    if not event_type and not push_type:
        LOG.debug("Webhook payload without event_type/push_type: %s", payload)
        return WebhookResult(home_id, event_type, push_type, WebhookKind.UNKNOWN)

    if push_type == WEBHOOK_DEVICE_EVENT:
        return await _process_device_event(account, payload)

    return _process_standard_envelope(account, home_id, event_type, push_type, payload)


def _process_standard_envelope(
    account: AsyncAccount,
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
    payload: dict[str, Any],
) -> WebhookResult:
    """Route the standard top-level-`event_type` envelope via `classify()`.

    Split out of `process_webhook` so `device_event` -- which carries no
    top-level `event_type` and is routed before `classify()` runs -- cannot
    reach here, keeping `classify()` pure for this envelope shape.
    """
    kind = classify(event_type, push_type)

    if kind is WebhookKind.LIFECYCLE:
        return _process_lifecycle(home_id, event_type, push_type)

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
            needs_refresh=True,
        )

    return WebhookResult(home_id, event_type, push_type, WebhookKind.UNKNOWN)


async def _process_device_event(
    account: AsyncAccount,
    payload: dict[str, Any],
) -> WebhookResult:
    """Route a `device_event` envelope by its `extra_params` contents.

    - `extra_params.modules[]` present -> STATE, merged via `Module.update`
      (reflection-based, so it keeps attributes absent from the partial
      payload, unlike `Room.update`).
    - else `extra_params.event_type` present (energy events such as
      `setpoint_event`/`temperature_variation_event`) -> EVENT, surfaced only;
      no state merge. These use a different key schema (`temperature`/
      `setpoint`/`ts_begin`/`ts_end`, not `therm_setpoint_*`) than the
      top-level `display_change` payload Netatmo also sends for the same
      change, which is the authoritative, cleanly-keyed source for the room
      merge -- merging both would double-apply.
    - else -> UNKNOWN, no mutation.
    """
    extra = _extra_params(payload)
    home_id = resolve_home_id(payload)
    modules = dict_entries(extra.get("modules"))

    if modules:
        touched = await _merge_device_modules(account, home_id, modules)
        return WebhookResult(
            home_id,
            str_or_none(extra.get("event_type")),
            WEBHOOK_DEVICE_EVENT,
            WebhookKind.STATE,
            touched_ids=touched,
        )

    event_type = str_or_none(extra.get("event_type"))
    if event_type:
        device_id = str_or_none(payload.get("device_id"))
        return WebhookResult(
            home_id,
            event_type,
            WEBHOOK_DEVICE_EVENT,
            WebhookKind.EVENT,
            touched_ids=[device_id] if device_id else [],
            events=[build_webhook_event(payload)],
        )

    return WebhookResult(home_id, None, WEBHOOK_DEVICE_EVENT, WebhookKind.UNKNOWN)


async def _merge_device_modules(
    account: AsyncAccount,
    home_id: str | None,
    modules: list[dict[str, Any]],
) -> list[str]:
    """Merge each module via `Module.update`, a safe partial merge.

    Unlike `Room.update`, `Module.update` is reflection-based and preserves
    attributes absent from the partial payload. Camera-category modules are
    skipped: `Camera.update` calls `async_update_camera_urls`, which performs
    network I/O and must never run on the webhook response path. Current
    `device_event` payloads only carry dimmers/switches, but this guards
    defensively against a future payload naming a camera.
    """
    home = account.homes.get(home_id) if home_id else None
    if home is None:
        return []
    touched: list[str] = []
    for module_data in modules:
        module_id = str_or_none(module_data.get("id"))
        module = home.modules.get(module_id) if module_id else None
        if module is None:
            continue
        if getattr(module, "device_category", None) == DeviceCategory.camera:
            continue
        await module.update(module_data)
        touched.append(module.entity_id)
    return touched


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
        return WebhookResult(home_id, event_type, push_type, WebhookKind.STATE)

    touched: list[str] = []
    if event_type in (
        EVENT_TYPE_SET_POINT,
        EVENT_TYPE_CANCEL_SET_POINT,
        EVENT_TYPE_SETPOINT_EVENT,
    ):
        touched = _merge_rooms(home, payload)
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
    elif event_type in (EVENT_TYPE_ON, EVENT_TYPE_OFF):
        touched = _merge_camera_monitoring(home, event_type, payload)
    elif event_type == EVENT_TYPE_LIGHT_MODE:
        touched = _merge_camera_floodlight(home, payload)

    return WebhookResult(
        home_id,
        event_type,
        push_type,
        WebhookKind.STATE,
        touched_ids=touched,
    )


def _merge_rooms(home: Home, payload: dict[str, Any]) -> list[str]:
    """Merge only the setpoint fields present in the payload into each room."""
    touched: list[str] = []
    home_data = payload.get("home")
    if not isinstance(home_data, dict):
        return touched
    for room in dict_entries(home_data.get("rooms")):
        room_id = str_or_none(room.get("id"))
        room_obj = home.rooms.get(room_id) if room_id else None
        if room_obj is None:
            continue
        if _merge_room_setpoints(room_obj, room):
            touched.append(room_obj.entity_id)
    return touched


def _merge_room_setpoints(room_obj: Room, room: dict[str, Any]) -> bool:
    """Apply the payload's setpoint fields to `room_obj`; return True if any stuck.

    An explicit `null` is honoured and clears the field, since that is how a
    cancelled setpoint arrives. A value of the wrong type is dropped instead,
    so a malformed payload cannot overwrite a known-good reading.
    """
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
) -> list[str]:
    camera_id = _camera_id(payload)
    if not camera_id:
        return []
    module = home.modules.get(camera_id)
    if module is None or not hasattr(module, "monitoring"):
        return []
    cast("MonitoringMixin", module).monitoring = event_type == EVENT_TYPE_ON
    return [camera_id]


def _merge_camera_floodlight(home: Home, payload: dict[str, Any]) -> list[str]:
    camera_id = _camera_id(payload)
    if not camera_id:
        return []
    module = home.modules.get(camera_id)
    sub_type = str_or_none(payload.get("sub_type"))
    if module is None or sub_type is None or not hasattr(module, "floodlight"):
        return []
    cast("FloodlightMixin", module).floodlight = sub_type
    return [camera_id]


def _touched_from_payload(payload: dict[str, Any]) -> list[str]:
    """De-duplicated device/camera/module ids referenced by the payload."""
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
        events=[build_webhook_event(payload)],
    )


def _process_lifecycle(
    home_id: str | None,
    event_type: str | None,
    push_type: str | None,
) -> WebhookResult:
    if push_type == WEBHOOK_ACTIVATION:
        lifecycle = LifecycleStatus.ACTIVATION
        needs_refresh = False
    elif push_type == WEBHOOK_DEACTIVATION:
        lifecycle = LifecycleStatus.DEACTIVATION
        needs_refresh = False
    else:  # camera reconnect
        lifecycle = LifecycleStatus.CONNECTION
        needs_refresh = True
    return WebhookResult(
        home_id,
        event_type,
        push_type,
        WebhookKind.LIFECYCLE,
        needs_refresh=needs_refresh,
        lifecycle=lifecycle,
    )
