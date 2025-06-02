"""Module to represent a Netatmo schedule."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from pyatmo.enums import ScheduleType
from pyatmo.modules.base_class import NetatmoBase
from pyatmo.room import Room

if TYPE_CHECKING:
    from pyatmo.const import RawData

    from .home import Home

LOG: logging.Logger = logging.getLogger(__name__)


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
        self.timetable = [
            TimetableEntry(home, r) for r in raw_data.get("timetable", [])
        ]
        self.zones = [Zone(home, r) for r in raw_data.get("zones", [])]

    def update_topology(self, raw_data: RawData) -> None:
        """Update the schedule topology."""
        super().update_topology(raw_data)

        self.selected = raw_data.get("selected", self.selected)
        self.default = raw_data.get("default", self.default)
        self.hg_temp = raw_data.get("hg_temp", self.hg_temp)
        self.away_temp = raw_data.get("away_temp", self.away_temp)
        self.cooling_away_temp = raw_data.get(
            "cooling_away_temp",
            self.cooling_away_temp,
        )
        self.timetable = [
            TimetableEntry(self.home, r) for r in raw_data.get("timetable", [])
        ]

        self.zones = [Zone(self.home, r) for r in raw_data.get("zones", [])]


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
class Zone(NetatmoBase):
    """Class to represent a Netatmo schedule's zone."""

    type: int
    rooms: list[Room]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's zone instance."""
        super().__init__(raw_data)
        self.home = home
        self.type = raw_data.get("type", 0)

        def room_factory(home: Home, room_raw_data: RawData) -> Room:
            room: Room = Room(home, room_raw_data, {})
            room.update(room_raw_data)
            return room

        self.rooms = [room_factory(home, r) for r in raw_data.get("rooms", [])]
