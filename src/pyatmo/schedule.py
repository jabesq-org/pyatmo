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

        self.selected = raw_data.get("selected", self.selected)
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
