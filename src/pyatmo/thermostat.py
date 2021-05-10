import logging
from collections import defaultdict
from typing import Any, Dict, Optional

from .auth import NetatmoOAuth2
from .exceptions import InvalidRoom, NoDevice, NoSchedule
from .helpers import _BASE_URL

LOG = logging.getLogger(__name__)

_GETHOMESDATA_REQ = _BASE_URL + "api/homesdata"
_GETHOMESTATUS_REQ = _BASE_URL + "api/homestatus"
_SETTHERMMODE_REQ = _BASE_URL + "api/setthermmode"
_SETROOMTHERMPOINT_REQ = _BASE_URL + "api/setroomthermpoint"
_GETROOMMEASURE_REQ = _BASE_URL + "api/getroommeasure"
_SWITCHHOMESCHEDULE_REQ = _BASE_URL + "api/switchhomeschedule"


class HomeData:
    """
    Class of Netatmo energy devices (relays, thermostat modules and valves)
    """

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token

        Raises:
            NoDevice: No devices found.
        """
        self.auth = auth
        resp = self.auth.post_request(url=_GETHOMESDATA_REQ)
        if resp is None or "body" not in resp:
            raise NoDevice("No thermostat data returned by Netatmo server")

        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No thermostat data available")

        self.homes: Dict = {d["id"]: d for d in self.raw_data}

        self.modules: Dict = defaultdict(dict)
        self.rooms: Dict = defaultdict(dict)
        self.schedules: Dict = defaultdict(dict)
        self.zones: Dict = defaultdict(dict)
        self.setpoint_duration: Dict = defaultdict(dict)

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

    def _get_selected_schedule(self, home_id: str) -> Dict:
        """Get the selected schedule for a given home ID."""
        for value in self.schedules.get(home_id, {}).values():
            if "selected" in value.keys():
                return value

        return {}

    def switch_home_schedule(self, home_id: str, schedule_id: str) -> Any:
        """Switch the schedule for a give home ID."""
        schedules = {
            self.schedules[home_id][s]["name"]: self.schedules[home_id][s]["id"]
            for s in self.schedules.get(home_id, {})
        }
        if schedule_id not in list(schedules.values()):
            raise NoSchedule("%s is not a valid schedule id" % schedule_id)

        post_params = {
            "home_id": home_id,
            "schedule_id": schedule_id,
        }
        resp = self.auth.post_request(url=_SWITCHHOMESCHEDULE_REQ, params=post_params)
        LOG.debug("Response: %s", resp)

    def get_hg_temp(self, home_id: str) -> Optional[float]:
        """Return frost guard temperature value."""
        return self._get_selected_schedule(home_id).get("hg_temp")

    def get_away_temp(self, home_id: str) -> Optional[float]:
        """Return the configured away temperature value."""
        return self._get_selected_schedule(home_id).get("away_temp")

    def get_thermostat_type(self, home_id: str, room_id: str) -> Optional[str]:
        """Return the thermostat type of the room."""
        for module in self.modules.get(home_id, {}).values():
            if module.get("room_id") == room_id:
                return module.get("type")

        return None


class HomeStatus:
    def __init__(self, auth: NetatmoOAuth2, home_id: str):
        self.auth = auth

        self.home_id = home_id
        post_params = {"home_id": self.home_id}

        resp = self.auth.post_request(url=_GETHOMESTATUS_REQ, params=post_params)
        if (
            "errors" in resp
            or "body" not in resp
            or "home" not in resp["body"]
            or ("errors" in resp["body"] and "modules" not in resp["body"]["home"])
        ):
            LOG.error("Errors in response: %s", resp)
            raise NoDevice("No device found, errors in response")

        self.raw_data = resp["body"]["home"]
        self.rooms: Dict = {}
        self.thermostats: Dict = defaultdict(dict)
        self.valves: Dict = defaultdict(dict)
        self.relays: Dict = defaultdict(dict)

        for room in self.raw_data.get("rooms", []):
            self.rooms[room["id"]] = room

        for module in self.raw_data.get("modules", []):
            if module["type"] == "NATherm1":
                self.thermostats[module["id"]] = module

            elif module["type"] == "NRV":
                self.valves[module["id"]] = module

            elif module["type"] == "NAPlug":
                self.relays[module["id"]] = module

    def get_room(self, room_id: str) -> Dict:
        for key, value in self.rooms.items():
            if value["id"] == room_id:
                return self.rooms[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def get_thermostat(self, room_id: str) -> Dict:
        """Return thermostat data for a given room id."""
        for key, value in self.thermostats.items():
            if value["id"] == room_id:
                return self.thermostats[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def get_relay(self, room_id: str) -> Dict:
        for key, value in self.relays.items():
            if value["id"] == room_id:
                return self.relays[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def get_valve(self, room_id: str) -> Dict:
        for key, value in self.valves.items():
            if value["id"] == room_id:
                return self.valves[key]

        raise InvalidRoom("No room with ID %s" % room_id)

    def set_point(self, room_id: str) -> Optional[float]:
        """Return the setpoint of a given room."""
        return self.get_room(room_id).get("therm_setpoint_temperature")

    def set_point_mode(self, room_id: str) -> Optional[str]:
        """Return the setpointmode of a given room."""
        return self.get_room(room_id).get("therm_setpoint_mode")

    def measured_temperature(self, room_id: str) -> Optional[float]:
        """Return the measured temperature of a given room."""
        return self.get_room(room_id).get("therm_measured_temperature")

    def boiler_status(self, module_id: str) -> Optional[bool]:
        return self.get_thermostat(module_id).get("boiler_status")

    def set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> Optional[str]:
        post_params = {
            "home_id": self.home_id,
            "mode": mode,
        }
        if end_time is not None and mode in ("hg", "away"):
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        return self.auth.post_request(url=_SETTHERMMODE_REQ, params=post_params)

    def set_room_thermpoint(
        self,
        room_id: str,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> Optional[str]:
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

        return self.auth.post_request(url=_SETROOMTHERMPOINT_REQ, params=post_params)
