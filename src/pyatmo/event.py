"""Module to represent a Netatmo event."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pyatmo.const import RawData

EVENT_ATTRIBUTES_MAP = {"id": "entity_id", "type": "event_type", "time": "event_time"}


class EventTypes(Enum):
    """Event types."""

    # temporarily disable locally-disabled and locally-enabled
    # pylint: disable=C0103

    movement = "movement"
    person = "person"
    person_away = "person_away"
    connection = "connection"
    disconnection = "disconnection"
    new_module = "new_module"
    module_connect = "module_connect"
    module_disconnect = "module_disconnect"
    module_low_battery = "module_low_battery"
    module_end_update = "module_end_update"
    on = "on"
    off = "off"
    sd = "sd"
    alim = "alim"
    boot = "boot"
    outdoor = "outdoor"
    daily_summary = "daily_summary"
    tag_big_move = "tag_big_move"
    tag_small_move = "tag_small_move"
    tag_uninstalled = "tag_uninstalled"
    tag_open = "tag_open"
    hush = "hush"
    smoke = "smoke"
    tampered = "tampered"
    wifi_status = "wifi_status"
    battery_status = "battery_status"
    detection_chamber_status = "detection_chamber_status"
    sound_test = "sound_test"
    siren_sounding = "siren_sounding"
    siren_tampered = "siren_tampered"
    incoming_call = "incoming_call"
    accepted_call = "accepted_call"
    missed_call = "missed_call"
    co_detected = "co_detected"

    # pylint: enable=C0103


class VideoStatus(Enum):
    """Video states."""

    # temporarily disable locally-disabled and locally-enabled
    # pylint: disable=C0103

    available = "available"
    deleted = "deleted"

    # pylint: enable=C0103


@dataclass
class Snapshot:
    """Class to represent a Netatmo event snapshot."""

    snapshot_id: str
    version: int
    key: str
    url: str


@dataclass
class Event:
    """Class to represent a Netatmo events."""

    entity_id: str
    event_type: EventTypes
    event_time: int
    message: str | None = None
    camera_id: str | None = None
    device_id: str | None = None
    person_id: str | None = None
    video_id: str | None = None
    sub_type: int | None = None
    snapshot: Snapshot | None = None
    vignette: Snapshot | None = None
    video_status: VideoStatus | None = None
    is_arrival: bool | None = None
    subevents: list[Event] | None = None

    def __init__(self, home_id: str, raw_data: RawData) -> None:
        self.home_id = home_id
        self._init_attributes(raw_data)

    def _init_attributes(self, raw_data: RawData) -> None:
        for attrib, value in raw_data.items():
            if attrib == "subevents":
                value = [Event(self.home_id, event) for event in value]
            setattr(self, EVENT_ATTRIBUTES_MAP.get(attrib, attrib), value)
