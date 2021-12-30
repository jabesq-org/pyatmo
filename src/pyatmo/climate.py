"""Support for Netatmo energy devices (relays, thermostats and valves)."""
from __future__ import annotations

import logging
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .exceptions import InvalidHome, NoSchedule
from .helpers import extract_raw_data_new
from .thermostat import (
    _GETHOMESDATA_REQ,
    _GETHOMESTATUS_REQ,
    _SETROOMTHERMPOINT_REQ,
    _SETTHERMMODE_REQ,
    _SWITCHHOMESCHEDULE_REQ,
)

LOG = logging.getLogger(__name__)


class NetatmoDeviceType(Enum):
    """Class to represent Netatmo device types."""

    # temporarily disable locally-disabled and locally-enabled@

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

    def __init__(self, raw_data: dict) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", "Unknown")
        self.modules = {
            module["id"]: NetatmoModule(home=self, module=module)
            for module in raw_data.get("modules", [])
        }
        self.rooms = {
            room["id"]: NetatmoRoom(
                home=self,
                room=room,
                all_modules=self.modules,
            )
            for room in raw_data.get("rooms", [])
        }
        self.schedules = {
            s["id"]: NetatmoSchedule(home_id=self.entity_id, raw_data=s)
            for s in raw_data.get("schedules", [])
        }

    def update_topology(self, raw_data: dict) -> None:
        self.name = raw_data.get("name", "Unknown")

        raw_modules = raw_data.get("modules", [])
        for module in raw_modules:
            if (module_id := module["id"]) not in self.modules:
                self.modules[module_id] = NetatmoModule(home=self, module=module)
            else:
                self.modules[module_id].update_topology(module)

        # Drop module if has been removed
        for module in self.modules.keys() - {m["id"] for m in raw_modules}:
            self.modules.pop(module)

        raw_rooms = raw_data.get("rooms", [])
        for room in raw_rooms:
            if (room_id := room["id"]) not in self.rooms:
                self.rooms[room_id] = NetatmoRoom(
                    home=self,
                    room=room,
                    all_modules=self.modules,
                )
            else:
                self.rooms[room_id].update_topology(room)

        # Drop room if has been removed
        for room in self.rooms.keys() - {m["id"] for m in raw_rooms}:
            self.rooms.pop(room)

        self.schedules = {
            s["id"]: NetatmoSchedule(home_id=self.entity_id, raw_data=s)
            for s in raw_data.get("schedules", [])
        }

    def update(self, raw_data: dict) -> None:
        for module in raw_data["errors"]:
            self.modules[module["id"]].update({})

        data = raw_data["home"]

        for module in data.get("modules", []):
            self.modules[module["id"]].update(module)

        for room in data.get("rooms", []):
            self.rooms[room["id"]].update(room)

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


@dataclass
class NetatmoRoom:
    """Class to represent a Netatmo room."""

    entity_id: str
    name: str
    home: NetatmoHome
    modules: dict[str, NetatmoModule]
    device_type: NetatmoDeviceType | None = None

    reachable: bool = False
    therm_setpoint_temperature: float | None = None
    therm_setpoint_mode: str | None = None
    therm_measured_temperature: float | None = None
    heating_power_request: int | None = None

    def __init__(
        self,
        home: NetatmoHome,
        room: dict,
        all_modules: dict[str, NetatmoModule],
    ) -> None:
        self.entity_id = room["id"]
        self.name = room["name"]
        self.home = home
        self.modules = {
            m_id: m
            for m_id, m in all_modules.items()
            if m_id in room.get("module_ids", [])
        }
        self.evaluate_device_type()

    def update_topology(self, raw_data: dict) -> None:
        self.name = raw_data["name"]
        self.modules = {
            m_id: m
            for m_id, m in self.home.modules.items()
            if m_id in raw_data.get("module_ids", [])
        }
        self.evaluate_device_type()

    def evaluate_device_type(self) -> None:
        for module in self.modules.values():
            if module.device_type is NetatmoDeviceType.NATherm1:
                self.device_type = NetatmoDeviceType.NATherm1
                break
            if module.device_type is NetatmoDeviceType.NRV:
                self.device_type = NetatmoDeviceType.NRV

    def update(self, raw_data: dict) -> None:
        self.reachable = raw_data.get("reachable", False)
        self.therm_measured_temperature = raw_data.get("therm_measured_temperature")
        self.therm_setpoint_mode = raw_data.get("therm_setpoint_mode")
        self.therm_setpoint_temperature = raw_data.get("therm_setpoint_temperature")
        self.heating_power_request = raw_data.get("heating_power_request")


@dataclass
class NetatmoSchedule:
    """Class to represent a Netatmo schedule."""

    entity_id: str
    name: str
    home_id: str
    selected: bool
    away_temp: float | None
    hg_temp: float | None

    def __init__(self, home_id: str, raw_data) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", f"Schedule {self.entity_id}")
        self.home_id = home_id
        self.selected = raw_data.get("selected", False)
        self.hg_temp = raw_data.get("hg_temp")
        self.away_temp = raw_data.get("away_temp")


@dataclass
class NetatmoModule:
    """Class to represent a Netatmo module."""

    entity_id: str
    name: str
    device_type: NetatmoDeviceType
    home: NetatmoHome
    room_id: str | None

    reachable: bool
    bridge: NetatmoModule | None
    modules: list[str]

    battery_state: str | None = None
    battery_level: int | None = None
    boiler_status: bool | None = None

    def __init__(self, home: NetatmoHome, module: dict) -> None:
        self.entity_id = module["id"]
        self.name = module.get("name", "Unkown")
        self.device_type = NetatmoDeviceType(module["type"])
        self.home = home
        self.room_id = module.get("room_id")
        self.reachable = False
        self.bridge = module.get("bridge")
        self.modules = module.get("modules_bridged", [])

    def update_topology(self, raw_data: dict) -> None:
        self.name = raw_data.get("name", "Unkown")
        self.device_type = NetatmoDeviceType(raw_data["type"])
        self.room_id = raw_data.get("room_id")
        self.bridge = raw_data.get("bridge")
        self.modules = raw_data.get("modules_bridged", [])

    def update(self, raw_data: dict) -> None:
        self.reachable = raw_data.get("reachable", False)
        self.boiler_status = raw_data.get("boiler_status")
        self.battery_level = raw_data.get("battery_level")
        self.battery_state = raw_data.get("battery_state")

        if not self.reachable:
            # Update bridged modules and associated rooms
            for module_id in self.modules:
                module = self.home.modules[module_id]
                module.update(raw_data)
                if module.room_id:
                    self.home.rooms[module.room_id].update(raw_data)


class AbstractClimate(ABC):
    """Abstract class of Netatmo energy devices."""

    home_id: str
    homes: dict = {}
    modules: dict = {}
    rooms: dict = {}
    schedules: dict = {}

    raw_data: dict | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(home_id={self.home_id})"

    def process(self, raw_data: dict) -> None:
        """Process raw status data from the energy endpoint."""
        if self.home_id != raw_data["home"]["id"]:
            raise InvalidHome(
                f"Home id '{raw_data['home']['id']}' does not match. '{self.home_id}'",
            )

        if self.home_id not in self.homes:
            self.raw_data = raw_data
            return

        self.homes[self.home_id].update(raw_data)
        self.raw_data = None

    def process_topology(self, raw_data: dict) -> None:
        """Process topology information from /homedata."""
        if self.home_id not in self.homes:
            self.homes[self.home_id] = NetatmoHome(raw_data=raw_data)
        else:
            self.homes[self.home_id].update_topology(raw_data)

        if self.raw_data:
            self.process(self.raw_data)


class AsyncClimate(AbstractClimate):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: AbstractAsyncAuth, home_id: str) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth
        self.home_id = home_id

    async def async_update(self) -> None:
        """Fetch and process data from API."""
        resp = await self.auth.async_post_request(
            url=_GETHOMESTATUS_REQ,
            params={"home_id": self.home_id},
        )
        raw_data = extract_raw_data_new(await resp.json(), "home")
        self.process(raw_data)

    async def async_set_room_thermpoint(
        self,
        room_id: str,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> str | None:
        """Set room temperature set point."""
        post_params = {
            "home_id": self.home_id,
            "room_id": room_id,
            "mode": mode,
        }
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            post_params["temp"] = str(temp)

        if end_time is not None:
            post_params["endtime"] = str(end_time)

        LOG.debug(
            "Setting room (%s) temperature set point to %s until %s",
            room_id,
            temp,
            end_time,
        )
        resp = await self.auth.async_post_request(
            url=_SETROOMTHERMPOINT_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> str | None:
        """Set thermotat mode."""
        if schedule_id is not None and not self.homes[self.home_id].is_valid_schedule(
            schedule_id,
        ):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id.")

        if mode is None:
            raise NoSchedule(f"{mode} is not a valid mode.")

        post_params = {"home_id": self.home_id, "mode": mode}
        if end_time is not None and mode in {"hg", "away"}:
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        LOG.debug("Setting home (%s) mode to %s (%s)", self.home_id, mode, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SETTHERMMODE_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_switch_home_schedule(self, schedule_id: str) -> None:
        """Switch the schedule for a give home ID."""
        if not self.homes[self.home_id].is_valid_schedule(schedule_id):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id")

        LOG.debug("Setting home (%s) schedule to %s", self.home_id, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SWITCHHOMESCHEDULE_REQ,
            params={"home_id": self.home_id, "schedule_id": schedule_id},
        )
        LOG.debug("Response: %s", resp)


class Climate(AbstractClimate):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
        """
        self.auth = auth

    def update(self) -> None:
        """Fetch and process data from API."""
        if not self.homes:
            LOG.debug('Topology for home "{self.home_id}" has not been initialized.')
            return

        resp = self.auth.post_request(url=_GETHOMESTATUS_REQ)

        raw_data = extract_raw_data_new(resp.json(), "home")
        self.process(raw_data)


class AbstractClimateTopology(ABC):
    """Abstract class of Netatmo energy device topology."""

    home_ids: list[str] = []
    subscriptions: dict[str, Callable] = {}
    raw_data: dict = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(home_ids={self.home_ids}, subscriptions={self.subscriptions})"

    def register_handler(self, home_id: str, handler: Callable) -> None:
        """Register update handler."""
        if self.subscriptions.get(home_id) == handler:
            return

        if home_id in self.subscriptions and self.subscriptions[home_id] != handler:
            self.unregister_handler(home_id)

        self.subscriptions[home_id] = handler

        self.publish()

    def unregister_handler(self, home_id: str) -> None:
        """Unregister update handler."""
        self.subscriptions.pop(home_id)

    def publish(self) -> None:
        """Publish latest data to subscribers."""
        for home in self.raw_data.get("homes", []):
            if (home_id := home["id"]) in self.subscriptions:
                self.subscriptions[home_id](home)


class AsyncClimateTopology(AbstractClimateTopology):
    """Async class of Netatmo energy device topology."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth

    async def async_update(self) -> None:
        """Retrieve status updates from /homesdata."""
        resp = await self.auth.async_post_request(url=_GETHOMESDATA_REQ)
        self.raw_data = extract_raw_data_new(await resp.json(), "homes")

        for home in self.raw_data["homes"]:
            self.home_ids.append(home["id"])

        self.publish()
