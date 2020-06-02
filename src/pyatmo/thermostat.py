import logging

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
    List of energy devices (relays, thermostat modules and valves)

    Args:
        auth (ClientAuth): Authentication information with a valid access token
    """

    def __init__(self, auth):
        self.auth = auth
        resp = self.auth.post_request(url=_GETHOMESDATA_REQ)
        if resp is None or "body" not in resp:
            raise NoDevice("No thermostat data returned by Netatmo server")

        self.rawData = resp["body"].get("homes")
        if not self.rawData:
            raise NoDevice("No thermostat data available")

        self.homes = {d["id"]: d for d in self.rawData}

        self.modules = {}
        self.rooms = {}
        self.schedules = {}
        self.zones = {}
        self.setpoint_duration = {}

        for item in self.rawData:
            home_id = item.get("id")
            nameHome = item.get("name")
            if not nameHome:
                nameHome = "Unknown"
                self.homes[home_id]["name"] = nameHome
            if "modules" in item:
                if home_id not in self.modules:
                    self.modules[home_id] = {}
                for m in item["modules"]:
                    self.modules[home_id][m["id"]] = m
                if home_id not in self.rooms:
                    self.rooms[home_id] = {}
                if home_id not in self.schedules:
                    self.schedules[home_id] = {}
                if home_id not in self.zones:
                    self.zones[home_id] = {}
                if home_id not in self.setpoint_duration:
                    self.setpoint_duration[home_id] = {}
                if "therm_setpoint_default_duration" in item:
                    self.setpoint_duration[home_id] = item[
                        "therm_setpoint_default_duration"
                    ]
                if "rooms" in item:
                    for room in item["rooms"]:
                        self.rooms[home_id][room["id"]] = room
                if "therm_schedules" in item:
                    for schedule in item["therm_schedules"]:
                        self.schedules[home_id][schedule["id"]] = schedule
                    for schedule in item["therm_schedules"]:
                        scheduleId = schedule["id"]
                        if scheduleId not in self.zones[home_id]:
                            self.zones[home_id][scheduleId] = {}
                        for zone in schedule["zones"]:
                            self.zones[home_id][scheduleId][zone["id"]] = zone

    def get_selected_schedule(self, home_id: str):
        """Get the selected schedule for a given home ID."""
        for key, value in self.schedules.get(home_id, {}).items():
            if "selected" in value.keys():
                return value
        return {}

    def switch_home_schedule(self, home_id: str, schedule_id: str):
        """."""
        schedules = {
            self.schedules[home_id][s]["name"]: self.schedules[home_id][s]["id"]
            for s in self.schedules.get(home_id)
        }
        if schedule_id not in list(schedules.values()):
            raise NoSchedule("%s is not a valid schedule id" % schedule_id)

        postParams = {
            "home_id": home_id,
            "schedule_id": schedule_id,
        }
        resp = self.auth.post_request(url=_SWITCHHOMESCHEDULE_REQ, params=postParams)
        LOG.debug("Response: %s", resp)

    def get_hg_temp(self, home_id: str) -> float:
        """Return frost guard temperature value."""
        return self.get_selected_schedule(home_id).get("hg_temp")

    def get_away_temp(self, home_id: str) -> float:
        """Return the configured away temperature value."""
        return self.get_selected_schedule(home_id).get("away_temp")

    def get_thermostat_type(self, home_id: str, room_id: str):
        """Return the thermostat type of the room."""
        for module in self.modules.get(home_id, {}).values():
            if module.get("room_id") == room_id:
                return module.get("type")


class HomeStatus:
    def __init__(self, auth, home_id):
        self.auth = auth

        self.home_id = home_id
        postParams = {"home_id": self.home_id}

        resp = self.auth.post_request(url=_GETHOMESTATUS_REQ, params=postParams)
        if (
            "errors" in resp
            or "body" not in resp
            or "home" not in resp["body"]
            or ("errors" in resp["body"] and "modules" not in resp["body"]["home"])
        ):
            LOG.error("Errors in response: %s", resp)
            raise NoDevice("No device found, errors in response")

        self.rawData = resp["body"]["home"]
        self.rooms = {}
        self.thermostats = {}
        self.valves = {}
        self.relays = {}

        for r in self.rawData.get("rooms", []):
            self.rooms[r["id"]] = r

        for module in self.rawData.get("modules", []):
            if module["type"] == "NATherm1":
                thermostatId = module["id"]
                if thermostatId not in self.thermostats:
                    self.thermostats[thermostatId] = {}
                self.thermostats[thermostatId] = module
            elif module["type"] == "NRV":
                valveId = module["id"]
                if valveId not in self.valves:
                    self.valves[valveId] = {}
                self.valves[valveId] = module
            elif module["type"] == "NAPlug":
                relayId = module["id"]
                if relayId not in self.relays:
                    self.relays[relayId] = {}
                self.relays[relayId] = module

    def get_room(self, room_id):
        for key, value in self.rooms.items():
            if value["id"] == room_id:
                return self.rooms[key]
        raise InvalidRoom("No room with ID %s" % room_id)

    def get_thermostat(self, room_id: str):
        """Return thermostat data for a given room id."""
        for key, value in self.thermostats.items():
            if value["id"] == room_id:
                return self.thermostats[key]
        raise InvalidRoom("No room with ID %s" % room_id)

    def get_relay(self, room_id: str):
        for key, value in self.relays.items():
            if value["id"] == room_id:
                return self.relays[key]
        raise InvalidRoom("No room with ID %s" % room_id)

    def get_valve(self, room_id: str):
        for key, value in self.valves.items():
            if value["id"] == room_id:
                return self.valves[key]
        raise InvalidRoom("No room with ID %s" % room_id)

    def set_point(self, room_id: str):
        """Return the setpoint of a given room."""
        return self.get_room(room_id).get("therm_setpoint_temperature")

    def set_point_mode(self, room_id: str):
        """Return the setpointmode of a given room."""
        return self.get_room(room_id).get("therm_setpoint_mode")

    def measured_temperature(self, room_id: str):
        """Return the measured temperature of a given room."""
        return self.get_room(room_id).get("therm_measured_temperature")

    def boiler_status(self, module_id: str):
        return self.get_thermostat(module_id).get("boiler_status")

    def set_thermmode(self, mode, end_time=None, schedule_id=None):
        postParams = {
            "home_id": self.home_id,
            "mode": mode,
        }
        if end_time is not None and mode in ("hg", "away"):
            postParams["endtime"] = end_time
        if schedule_id is not None and mode == "schedule":
            postParams["schedule_id"] = schedule_id
        return self.auth.post_request(url=_SETTHERMMODE_REQ, params=postParams)

    def set_room_thermpoint(self, room_id: str, mode: str, temp=None, end_time=None):
        postParams = {
            "home_id": self.home_id,
            "room_id": room_id,
            "mode": mode,
        }
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            postParams["temp"] = temp
        if end_time is not None:
            postParams["endtime"] = end_time
        return self.auth.post_request(url=_SETROOMTHERMPOINT_REQ, params=postParams)
