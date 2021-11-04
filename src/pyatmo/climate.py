"""Support for Netatmo energy devices (relays, thermostats and valves)."""
from __future__ import annotations

import logging
from abc import ABC
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .helpers import extract_raw_data
from .thermostat import _GETHOMESDATA_REQ

LOG = logging.getLogger(__name__)

# pylint: disable=W0613,R0201


class NetatmoDeviceType(Enum):
    """Class to represent Netatmo device types."""

    # temporarily disable locally-disabled and locally-enabled
    # pylint: disable=I0011,C0103

    # Climate/Energy
    NRV = "NRV"  # Smart valve
    NATherm1 = "NATherm1"  # Smart thermostat
    OTM = "OTM"  # OpenTherm modulating thermostat
    NAPlug = "NAPlug"  # Relay
    OTH = "OTH"  # OpenTherm relay

    # Cameras/Security
    NOC = "NOC"  # Smart Outdoor Camera (with Siren)
    NACamera = "NACamera"  # Smart Indoor Camera
    NSD = "NSD"  # Smart Smoke Detector
    NIS = "NIS"  # Smart Indoor Siren
    NACamDoorTag = "NACamDoorTag"  # Smart Door and Window Sensors

    # Weather
    NAMain = "NAMain"  # Smart Home Weather Station
    NAModule1 = "NAModule1"
    NAModule2 = "NAModule2"
    NAModule3 = "NAModule3"
    NAModule4 = "NAModule4"

    # Home Coach
    NHC = "NHC"  # Smart Indoor Air Quality Monitor

    # pylint: enable=I0011,C0103


@dataclass
class NetatmoHome:
    """Class to represent a Netatmo home."""

    entity_id: str
    name: str
    rooms: dict[str, NetatmoRoom]
    modules: dict[str, NetatmoModule]
    schedules: dict[str, NetatmoSchedule]

    def get_selected_schedule(self) -> NetatmoSchedule | None:
        """Return selected schedule for given home."""
        for schedule in self.schedules.values():
            if schedule.selected:
                return schedule
        return None

    def is_valid_schedule(self, schedule_id: str) -> bool:
        """Check if valid schedule."""
        return schedule_id in self.schedules

    def get_hg_temp(self) -> float | None:
        """Return frost guard temperature value for given home."""
        if (schedule := self.get_selected_schedule()) is None:
            return None
        return schedule.hg_temp

    def get_away_temp(self) -> float | None:
        """Return configured away temperature value for given home."""
        if (schedule := self.get_selected_schedule()) is None:
            return None
        return schedule.away_temp

    async def async_set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> str | None:
        """Set thermotat mode."""
        ...

    async def async_switch_home_schedule(self, schedule_id: str) -> None:
        """Switch the schedule for a give home ID."""
        ...


@dataclass
class NetatmoRoom:
    """Class to represent a Netatmo room."""

    entity_id: str
    name: str
    home_id: str
    modules: dict[str, NetatmoModule]

    reachable: bool
    therm_setpoint_temperature: float | None
    therm_setpoint_mode: str | None
    therm_measured_temperature: float | None
    boiler_status: bool | None

    async def async_set_room_thermpoint(
        self,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> str | None:
        """Set room themperature set point."""
        ...


@dataclass
class NetatmoSchedule:
    """Class to represent a Netatmo room."""

    entity_id: str
    name: str
    home_id: str
    selected: bool
    away_temp: float | None
    hg_temp: float | None


@dataclass
class NetatmoModule:
    """Class to represent a Netatmo module."""

    entity_id: str
    name: str
    device_type: Enum
    home_id: str
    room_id: str

    reachable: bool
    bridge: NetatmoModule | None
    modules: list[NetatmoModule]


class AbstractClimate(ABC):
    """Abstract class of Netatmo energy devices."""

    raw_data: dict = defaultdict(dict)
    homes: dict = defaultdict(dict)
    modules: dict = defaultdict(dict)
    rooms: dict = defaultdict(dict)
    thermostats: dict = defaultdict(dict)
    valves: dict = defaultdict(dict)
    relays: dict = defaultdict(dict)
    errors: dict = defaultdict(dict)
    schedules: dict = defaultdict(dict)
    zones: dict = defaultdict(dict)
    setpoint_duration: dict = defaultdict(dict)

    topology_timestamp: int | None

    def process(self, raw_data: dict) -> None:
        """Process raw data from the energy endpoint."""
        for item in raw_data:
            modules = {
                m["id"]: NetatmoModule(
                    entity_id=m["id"],
                    name=m["name"],
                    device_type=m["type"],
                    home_id=item["id"],
                    room_id=m.get("room_id"),
                    reachable=False,
                    bridge=m.get("bridge"),
                    modules=m.get("modules"),
                )
                for m in item.get("modules", [])
            }
            rooms = {
                r["id"]: NetatmoRoom(
                    entity_id=r["id"],
                    name=r["name"],
                    home_id=item["id"],
                    modules=modules,
                    reachable=r.get("reachable", False),
                    therm_measured_temperature=r.get("therm_measured_temperature"),
                    therm_setpoint_mode=r.get(""),
                    therm_setpoint_temperature=r.get(""),
                    boiler_status=r.get(""),
                )
                for r in item.get("rooms", [])
            }
            schedules = {
                s["id"]: NetatmoSchedule(
                    entity_id=s["id"],
                    name=s["name"],
                    home_id=item["id"],
                    selected=s.get("selected", False),
                    hg_temp=s.get("hg_temp"),
                    away_temp=s.get("away_temp"),
                )
                for s in item.get("schedules", [])
            }
            self.homes[item["id"]] = NetatmoHome(
                entity_id=item["id"],
                name=item.get("name", "Unknown"),
                rooms=rooms,
                modules=modules,
                schedules=schedules,
            )


class Climate(AbstractClimate):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
        """
        self.auth = auth

    def update(self):
        """Fetch and process data from API."""
        if not self.homes:
            self.update_topology()

    def update_topology(self) -> None:
        """Retrieve status updates from /homesdata."""
        resp = self.auth.post_request(url=_GETHOMESDATA_REQ)

        raw_data = extract_raw_data(resp.json(), "homes")
        self.process(raw_data)


class AsyncClimate(AbstractClimate):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth

    async def async_update(self):
        """Fetch and process data from API."""
        if not self.homes:
            await self.async_update_topology()

    async def async_update_topology(self) -> None:
        """Retrieve status updates from /homesdata."""
        resp = await self.auth.async_post_request(url=_GETHOMESDATA_REQ)
        raw_data = extract_raw_data(await resp.json(), "homes")
        self.process(raw_data)
