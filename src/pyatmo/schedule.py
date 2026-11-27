"""Module to represent a Netatmo schedule."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import logging
from operator import itemgetter
from typing import TYPE_CHECKING

from pyatmo.enums import ScheduleType
from pyatmo.modules.base_class import NetatmoBase
from pyatmo.room import Room

if TYPE_CHECKING:
    from pyatmo.const import RawData

    from .home import Home

LOG: logging.Logger = logging.getLogger(__name__)

# Timetable offsets are minutes since Monday 00:00, home local time.
MINUTES_PER_DAY = 24 * 60
MINUTES_PER_WEEK = 7 * MINUTES_PER_DAY


@dataclass
class Schedule(NetatmoBase):
    """Class to represent a Netatmo schedule."""

    type: ScheduleType
    away_temp: float | None
    hg_temp: float | None
    cooling_away_temp: float | None
    timetable: list[TimetableEntry]
    selected: bool
    default: bool

    # electricity / electricity_production schedule fields
    tariff: str | None
    tariff_option: str | None
    power_threshold: int | None
    contract_power_unit: str | None

    # event schedule twilight timetables
    timetable_sunrise: list[TwilightEntry]
    timetable_sunset: list[TwilightEntry]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule instance."""
        super().__init__(raw_data)
        self.home = home
        self.type = ScheduleType(raw_data.get("type", ScheduleType.THERM))
        self.default = raw_data.get("default", False)
        self.selected = raw_data.get("selected", False)
        self.hg_temp = raw_data.get("hg_temp")
        self.away_temp = raw_data.get("away_temp")
        self.cooling_away_temp = raw_data.get("cooling_away_temp")
        self.tariff = raw_data.get("tariff")
        self.tariff_option = raw_data.get("tariff_option")
        self.power_threshold = raw_data.get("power_threshold")
        self.contract_power_unit = raw_data.get("contract_power_unit")
        self.timetable = [
            TimetableEntry(home, r) for r in raw_data.get("timetable", [])
        ]
        self.timetable_sunrise = [
            TwilightEntry(home, r) for r in raw_data.get("timetable_sunrise", [])
        ]
        self.timetable_sunset = [
            TwilightEntry(home, r) for r in raw_data.get("timetable_sunset", [])
        ]
        self.zones = [Zone(home, r) for r in raw_data.get("zones", [])]

    def update_topology(self, raw_data: RawData) -> None:
        """Update the schedule topology."""
        super().update_topology(raw_data)

        # /homesdata only sets "selected" on the currently selected schedule and
        # omits the key everywhere else, so an absent key means "not selected".
        self.selected = raw_data.get("selected", False)
        self.default = raw_data.get("default", self.default)
        self.hg_temp = raw_data.get("hg_temp", self.hg_temp)
        self.away_temp = raw_data.get("away_temp", self.away_temp)
        self.cooling_away_temp = raw_data.get(
            "cooling_away_temp",
            self.cooling_away_temp,
        )
        self.tariff = raw_data.get("tariff", self.tariff)
        self.tariff_option = raw_data.get("tariff_option", self.tariff_option)
        self.power_threshold = raw_data.get("power_threshold", self.power_threshold)
        self.contract_power_unit = raw_data.get(
            "contract_power_unit",
            self.contract_power_unit,
        )
        self.timetable = [
            TimetableEntry(self.home, r) for r in raw_data.get("timetable", [])
        ]
        self.timetable_sunrise = [
            TwilightEntry(self.home, r) for r in raw_data.get("timetable_sunrise", [])
        ]
        self.timetable_sunset = [
            TwilightEntry(self.home, r) for r in raw_data.get("timetable_sunset", [])
        ]

        self.zones = [Zone(self.home, r) for r in raw_data.get("zones", [])]

    def get_zone(self, zone_id: int | str | None) -> Zone | None:
        """Return the zone with the given id, if any.

        Zone ids are integers in timetables but may come back as strings in
        zone definitions, so they are compared as strings.
        """
        if zone_id is None:
            return None
        return next(
            (zone for zone in self.zones if str(zone.entity_id) == str(zone_id)),
            None,
        )

    def get_zone_at(self, week_minute: int) -> Zone | None:
        """Return the zone the timetable sets at the given minute of the week.

        `week_minute` counts minutes since Monday 00:00, home local time, like
        the timetable `m_offset`. The timetable repeats every week, so a minute
        before the first entry belongs to the last entry of the week.
        """
        entries = sorted(
            (
                (entry.m_offset, entry.zone_id)
                for entry in self.timetable
                if entry.m_offset is not None
            ),
            key=itemgetter(0),
        )
        if not entries:
            return None

        # Index -1 (a minute before the first entry) wraps to the last entry.
        index = bisect_right(entries, week_minute % MINUTES_PER_WEEK, key=itemgetter(0))
        return self.get_zone(entries[index - 1][1])


@dataclass
class TimetableEntry:
    """Class to represent a Netatmo schedule's timetable entry."""

    zone_id: int | None
    m_offset: int | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's timetable entry instance."""
        self.home = home
        self.zone_id = raw_data.get("zone_id", 0)
        self.m_offset = raw_data.get("m_offset", 0)


@dataclass
class TwilightEntry:
    """Class to represent an event schedule's sunrise/sunset timetable entry."""

    zone_id: int | None
    day: int | None
    twilight_offset: int | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's twilight timetable entry instance."""
        self.home = home
        self.zone_id = raw_data.get("zone_id", 0)
        self.day = raw_data.get("day")
        self.twilight_offset = raw_data.get("twilight_offset")


@dataclass
class ZoneModule(NetatmoBase):
    """Class to represent an event schedule zone's per-module action."""

    bridge: str | None
    on: bool | None
    target_position: int | None
    brightness: int | None
    fan_speed: int | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule zone's module action instance."""
        super().__init__(raw_data)
        self.home = home
        self.bridge = raw_data.get("bridge")
        self.on = raw_data.get("on")
        self.target_position = raw_data.get("target_position")
        self.brightness = raw_data.get("brightness")
        self.fan_speed = raw_data.get("fan_speed")


@dataclass
class Zone(NetatmoBase):
    """Class to represent a Netatmo schedule's zone."""

    type: int
    rooms: list[Room]
    rooms_temp: dict[str, float]

    # electricity schedule zone fields
    price_type: str | None
    price_value: float | None

    # event schedule zone module actions
    modules: list[ZoneModule]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's zone instance."""
        super().__init__(raw_data)
        self.home = home
        self.type = raw_data.get("type", 0)
        self.price_type = raw_data.get("price_type")
        self.price_value = raw_data.get("price_value")
        self.modules = [ZoneModule(home, r) for r in raw_data.get("modules", [])]

        def room_factory(home: Home, room_raw_data: RawData) -> Room:
            room: Room = Room(home, room_raw_data, {})
            room.update(room_raw_data)
            return room

        self.rooms = [room_factory(home, r) for r in raw_data.get("rooms", [])]
        # Zone setpoints are also listed in `rooms_temp`, the only list some
        # payloads carry. Malformed entries are skipped rather than failing the
        # whole topology update.
        self.rooms_temp = {
            str(r["room_id"]): r["temp"]
            for r in raw_data.get("rooms_temp") or []
            if isinstance(r, dict) and "room_id" in r and "temp" in r
        }

    def get_room_setpoint(self, room_id: str) -> float | None:
        """Return the setpoint this zone sets for the given room, if any."""
        room = next(
            (room for room in self.rooms if str(room.entity_id) == str(room_id)),
            None,
        )
        if room is not None:
            if room.therm_setpoint_temperature is not None:
                return room.therm_setpoint_temperature
            if room.cooling_setpoint_temperature is not None:
                return room.cooling_setpoint_temperature
        return self.rooms_temp.get(str(room_id))
