"""Support for Netatmo energy devices (relays, thermostats and valves)."""
from __future__ import annotations

import logging
from abc import ABC
from collections import defaultdict
from typing import Any

from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .exceptions import InvalidRoom, NoSchedule
from .helpers import _BASE_URL, extract_raw_data

LOG = logging.getLogger(__name__)

_GETHOMESDATA_REQ = _BASE_URL + "api/homesdata"
_GETHOMESTATUS_REQ = _BASE_URL + "api/homestatus"
_SETTHERMMODE_REQ = _BASE_URL + "api/setthermmode"
_SETROOMTHERMPOINT_REQ = _BASE_URL + "api/setroomthermpoint"
_GETROOMMEASURE_REQ = _BASE_URL + "api/getroommeasure"
_SWITCHHOMESCHEDULE_REQ = _BASE_URL + "api/switchhomeschedule"


class AbstractHomeData(ABC):
    """Abstract class of Netatmo energy devices."""

    raw_data: dict = defaultdict(dict)
    homes: dict = defaultdict(dict)
    modules: dict = defaultdict(dict)
    rooms: dict = defaultdict(dict)
    schedules: dict = defaultdict(dict)
    zones: dict = defaultdict(dict)
    setpoint_duration: dict = defaultdict(dict)

    def process(self) -> None:
        """Process data from API."""
        self.homes = {d["id"]: d for d in self.raw_data}

        for item in self.raw_data:
            home_id = item.get("id")
            home_name = item.get("name")

            if not home_name:
                home_name = "Unknown"
                self.homes[home_id]["name"] = home_name

            if "modules" not in item:
                continue

            for module in item["modules"]:
                self.modules[home_id][module["id"]] = module

            self.setpoint_duration[home_id] = item.get(
                "therm_setpoint_default_duration",
            )

            for room in item.get("rooms", []):
                self.rooms[home_id][room["id"]] = room

            for schedule in item.get("schedules", []):
                schedule_id = schedule["id"]
                self.schedules[home_id][schedule_id] = schedule

                if schedule_id not in self.zones[home_id]:
                    self.zones[home_id][schedule_id] = {}

                for zone in schedule["zones"]:
                    self.zones[home_id][schedule_id][zone["id"]] = zone

    def _get_selected_schedule(self, home_id: str) -> dict:
        """Get the selected schedule for a given home ID."""
        for value in self.schedules.get(home_id, {}).values():
            if "selected" in value.keys():
                return value

        return {}

    def get_hg_temp(self, home_id: str) -> float | None:
        """Return frost guard temperature value."""
        return self._get_selected_schedule(home_id).get("hg_temp")

    def get_away_temp(self, home_id: str) -> float | None:
        """Return the configured away temperature value."""
        return self._get_selected_schedule(home_id).get("away_temp")

    def get_thermostat_type(self, home_id: str, room_id: str) -> str | None:
        """Return the thermostat type of the room."""
        for module in self.modules.get(home_id, {}).values():
            if module.get("room_id") == room_id:
                return module.get("type")

        return None

    def is_valid_schedule(self, home_id: str, schedule_id: str):
        """Check if valid schedule."""
        schedules = {
            self.schedules[home_id][s]["name"]: self.schedules[home_id][s]["id"]
            for s in self.schedules.get(home_id, {})
        }
        return schedule_id in list(schedules.values())


class HomeData(AbstractHomeData):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
        """
        self.auth = auth

    def update(self) -> None:
        """Fetch and process data from API."""
        resp = self.auth.post_request(url=_GETHOMESDATA_REQ)

        self.raw_data = extract_raw_data(resp.json(), "homes")
        self.process()

    def switch_home_schedule(self, home_id: str, schedule_id: str) -> Any:
        """Switch the schedule for a give home ID."""
        if not self.is_valid_schedule(home_id, schedule_id):
            raise NoSchedule("%s is not a valid schedule id" % schedule_id)

        post_params = {"home_id": home_id, "schedule_id": schedule_id}
        resp = self.auth.post_request(url=_SWITCHHOMESCHEDULE_REQ, params=post_params)
        LOG.debug("Response: %s", resp)


class AsyncHomeData(AbstractHomeData):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth

    async def async_update(self):
        """Fetch and process data from API."""
        resp = await self.auth.async_post_request(url=_GETHOMESDATA_REQ)

        assert not isinstance(resp, bytes)
        self.raw_data = extract_raw_data(await resp.json(), "homes")
        self.process()

    async def async_switch_home_schedule(self, home_id: str, schedule_id: str) -> None:
        """Switch the schedule for a give home ID."""
        if not self.is_valid_schedule(home_id, schedule_id):
            raise NoSchedule("%s is not a valid schedule id" % schedule_id)

        post_params = {"home_id": home_id, "schedule_id": schedule_id}
        resp = await self.auth.async_post_request(
            url=_SWITCHHOMESCHEDULE_REQ,
            params=post_params,
        )
        LOG.debug("Response: %s", resp)


class AbstractHomeStatus(ABC):
    """Abstract class of the Netatmo home status."""

    raw_data: dict = defaultdict(dict)
    rooms: dict = defaultdict(dict)
    thermostats: dict = defaultdict(dict)
    valves: dict = defaultdict(dict)
    relays: dict = defaultdict(dict)

    def process(self) -> None:
        """Process data from API."""
        for room in self.raw_data.get("rooms", []):
            self.rooms[room["id"]] = room

        for module in self.raw_data.get("modules", []):
            if module["type"] in {"NATherm1", "OTM"}:
                self.thermostats[module["id"]] = module

            elif module["type"] == "NRV":
                self.valves[module["id"]] = module

            elif module["type"] in {"OTH", "NAPlug"}:
                self.relays[module["id"]] = module

    def get_room(self, room_id: str) -> dict:
        """Return room data for a given room id."""
        for key, value in self.rooms.items():
            if value["id"] == room_id:
                return self.rooms[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def get_thermostat(self, room_id: str) -> dict:
        """Return thermostat data for a given room id."""
        for key, value in self.thermostats.items():
            if value["id"] == room_id:
                return self.thermostats[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def get_relay(self, room_id: str) -> dict:
        """Return relay data for a given room id."""
        for key, value in self.relays.items():
            if value["id"] == room_id:
                return self.relays[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def get_valve(self, room_id: str) -> dict:
        """Return valve data for a given room id."""
        for key, value in self.valves.items():
            if value["id"] == room_id:
                return self.valves[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def set_point(self, room_id: str) -> float | None:
        """Return the setpoint of a given room."""
        return self.get_room(room_id).get("therm_setpoint_temperature")

    def set_point_mode(self, room_id: str) -> str | None:
        """Return the setpointmode of a given room."""
        return self.get_room(room_id).get("therm_setpoint_mode")

    def measured_temperature(self, room_id: str) -> float | None:
        """Return the measured temperature of a given room."""
        return self.get_room(room_id).get("therm_measured_temperature")

    def boiler_status(self, module_id: str) -> bool | None:
        """Return the status of the boiler status."""
        return self.get_thermostat(module_id).get("boiler_status")


class HomeStatus(AbstractHomeStatus):
    """Class of the Netatmo home status."""

    def __init__(self, auth: NetatmoOAuth2, home_id: str):
        """Initialize the Netatmo home status.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
            home_id {str} -- ID for targeted home
        """
        self.auth = auth

        self.home_id = home_id

    def update(self) -> None:
        """Fetch and process data from API."""
        post_params = {"home_id": self.home_id}

        resp = self.auth.post_request(url=_GETHOMESTATUS_REQ, params=post_params)

        self.raw_data = extract_raw_data(resp.json(), "home")
        self.process()

    def set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> str | None:
        """Set thermotat mode."""
        post_params = {"home_id": self.home_id, "mode": mode}
        if end_time is not None and mode in {"hg", "away"}:
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        return self.auth.post_request(url=_SETTHERMMODE_REQ, params=post_params).json()

    def set_room_thermpoint(
        self,
        room_id: str,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> str | None:
        """Set room themperature set point."""
        post_params = {"home_id": self.home_id, "room_id": room_id, "mode": mode}
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            post_params["temp"] = str(temp)

        if end_time is not None:
            post_params["endtime"] = str(end_time)

        return self.auth.post_request(
            url=_SETROOMTHERMPOINT_REQ,
            params=post_params,
        ).json()


class AsyncHomeStatus(AbstractHomeStatus):
    """Class of the Netatmo home status."""

    def __init__(self, auth: AbstractAsyncAuth, home_id: str):
        """Initialize the Netatmo home status.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
            home_id {str} -- ID for targeted home
        """
        self.auth = auth

        self.home_id = home_id

    async def async_update(self) -> None:
        """Fetch and process data from API."""
        post_params = {"home_id": self.home_id}

        resp = await self.auth.async_post_request(
            url=_GETHOMESTATUS_REQ,
            params=post_params,
        )

        assert not isinstance(resp, bytes)
        self.raw_data = extract_raw_data(await resp.json(), "home")
        self.process()

    async def async_set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> str | None:
        """Set thermotat mode."""
        post_params = {"home_id": self.home_id, "mode": mode}
        if end_time is not None and mode in {"hg", "away"}:
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        resp = await self.auth.async_post_request(
            url=_SETTHERMMODE_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_set_room_thermpoint(
        self,
        room_id: str,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> str | None:
        """Set room themperature set point."""
        post_params = {"home_id": self.home_id, "room_id": room_id, "mode": mode}
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            post_params["temp"] = str(temp)

        if end_time is not None:
            post_params["endtime"] = str(end_time)

        resp = await self.auth.async_post_request(
            url=_SETROOMTHERMPOINT_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()
