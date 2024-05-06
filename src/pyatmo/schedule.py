"""Module to represent a Netatmo schedule."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from pyatmo.const import (
    SCHEDULE_TYPE_COOLING,
    SCHEDULE_TYPE_ELECTRICITY,
    SCHEDULE_TYPE_EVENT,
    SCHEDULE_TYPE_THERM,
    RawData,
)
from pyatmo.modules.base_class import NetatmoBase
from pyatmo.room import Room

if TYPE_CHECKING:
    from .home import Home

LOG = logging.getLogger(__name__)


@dataclass
class Schedule(NetatmoBase):
    """Class to represent a Netatmo schedule."""

    selected: bool
    default: bool
    type: str
    timetable: list[TimetableEntry]
    zones: list[Zone]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule instance."""
        super().__init__(raw_data)
        self.home = home
        self.type = raw_data.get("type", "therm")
        self.selected = raw_data.get("selected", False)
        self.default = raw_data.get("default", False)
        self.timetable = [
            TimetableEntry(home, r) for r in raw_data.get("timetable", [])
        ]
        self.zones = [Zone(home, r) for r in raw_data.get("zones", [])]


@dataclass
class ScheduleWithRealZones(Schedule):
    """Class to represent a Netatmo schedule."""

    zones: list[Zone]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule instance."""
        super().__init__(home, raw_data)
        self.zones = [Zone(home, r) for r in raw_data.get("zones", [])]


@dataclass
class ThermSchedule(ScheduleWithRealZones):
    """Class to represent a Netatmo Temperature schedule."""

    away_temp: float | None
    hg_temp: float | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize ThermSchedule."""
        super().__init__(home, raw_data)
        self.hg_temp = raw_data.get("hg_temp")
        self.away_temp = raw_data.get("away_temp")


@dataclass
class CoolingSchedule(ThermSchedule):
    """Class to represent a Netatmo Cooling schedule."""

    cooling_away_temp: float | None
    hg_temp: float | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize CoolingSchedule."""
        super().__init__(home, raw_data)
        self.cooling_away_temp = self.away_temp = raw_data.get(
            "cooling_away_temp", self.away_temp
        )


@dataclass
class ElectricitySchedule(Schedule):
    """Class to represent a Netatmo Energy Plan schedule."""

    tariff: str
    tariff_option: str
    power_threshold: int | 6
    contract_power_unit: str  # kVA or KW
    zones: list[ZoneElectricity]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize ElectricitySchedule."""
        super().__init__(home, raw_data)
        self.tariff = raw_data.get("tariff", "custom")
        # Tariff option (basic = always the same price, peak_and_off_peak = peak & offpeak hours)
        self.tariff_option = raw_data.get("tariff_option", "basic")
        self.power_threshold = raw_data.get("power_threshold", 6)
        self.contract_power_unit = raw_data.get("power_threshold", "kVA")
        self.zones = [ZoneElectricity(home, r) for r in raw_data.get("zones", [])]


@dataclass
class EventSchedule(Schedule):
    """Class to represent a Netatmo Energy Plan schedule."""

    timetable_sunrise: list[TimetableEventEntry]
    timetable_sunset: list[TimetableEventEntry]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize EventSchedule."""
        super().__init__(home, raw_data)
        self.timetable_sunrise = [
            TimetableEventEntry(home, r) for r in raw_data.get("timetable_sunrise", [])
        ]
        self.timetable_sunset = [
            TimetableEventEntry(home, r) for r in raw_data.get("timetable_sunset", [])
        ]


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
        self.twilight_offset = raw_data.get("twilight_offset", 0)


@dataclass
class TimetableEventEntry:
    """Class to represent a Netatmo schedule's timetable entry."""

    zone_id: int | None
    day: int | 1
    twilight_offset: int | 0

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's timetable entry instance."""
        self.home = home
        self.zone_id = raw_data.get("zone_id", 0)
        self.day = raw_data.get("day", 1)
        self.twilight_offset = raw_data.get("twilight_offset", 0)


class ModuleSchedule(NetatmoBase):
    """Class to represent a Netatmo schedule."""

    on: bool | None
    target_position: int | None
    fan_speed: int | None
    brightness: int | None

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's zone instance."""
        super().__init__(raw_data)
        self.home = home
        self.on = raw_data.get("on", None)
        self.target_position = raw_data.get("target_position", None)
        self.fan_speed = raw_data.get("fan_speed", None)
        self.brightness = raw_data.get("brightness", None)


@dataclass
class Zone(NetatmoBase):
    """Class to represent a Netatmo schedule's zone."""

    type: int
    rooms: list[Room]
    modules: list[ModuleSchedule]

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's zone instance."""
        super().__init__(raw_data)
        self.home = home
        self.type = raw_data.get("type", 0)

        def room_factory(room_home: Home, room_raw_data: RawData):
            room = Room(room_home, room_raw_data, {})
            room.update(room_raw_data)
            return room

        self.rooms = [room_factory(home, r) for r in raw_data.get("rooms", [])]
        self.modules = [ModuleSchedule(home, m) for m in raw_data.get("modules", [])]


@dataclass
class ZoneElectricity(NetatmoBase):
    """Class to represent a Netatmo schedule's zone."""

    price: float
    price_type: str

    def __init__(self, home: Home, raw_data: RawData) -> None:
        """Initialize a Netatmo schedule's zone instance."""
        super().__init__(raw_data)
        self.home = home
        self.price = raw_data.get("price", 0.0)
        self.price_type = raw_data.get("price_type", "off_peak")


def schedule_factory(home: Home, raw_data: RawData) -> (Schedule, str):
    """Create proper schedules."""

    schedule_type = raw_data.get("type", "custom")
    cls = {
        SCHEDULE_TYPE_THERM: ThermSchedule,
        SCHEDULE_TYPE_EVENT: EventSchedule,
        SCHEDULE_TYPE_ELECTRICITY: ElectricitySchedule,
        SCHEDULE_TYPE_COOLING: CoolingSchedule,
    }.get(schedule_type, Schedule)
    return cls(home, raw_data), schedule_type
