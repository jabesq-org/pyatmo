import logging

from pyatmo.exceptions import InvalidHome, InvalidRoom, NoDevice, NoSchedule
from pyatmo.helpers import BASE_URL

LOG = logging.getLogger(__name__)

_GETHOMESDATA_REQ = BASE_URL + "api/homesdata"
_GETHOMESTATUS_REQ = BASE_URL + "api/homestatus"
_SETTHERMMODE_REQ = BASE_URL + "api/setthermmode"
_SETROOMTHERMPOINT_REQ = BASE_URL + "api/setroomthermpoint"
_GETROOMMEASURE_REQ = BASE_URL + "api/getroommeasure"
_SWITCHHOMESCHEDULE_REQ = BASE_URL + "api/switchhomeschedule"


class HomeData:
    """
    List the Energy devices (relays, thermostat modules and valves)

    Args:
        auth_data (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, auth_data):
        self.auth_data = auth_data
        resp = self.auth_data.post_request(url=_GETHOMESDATA_REQ)
        if resp is None or "body" not in resp:
            raise NoDevice("No thermostat data returned by Netatmo server")
        self.raw_data = resp["body"].get("homes")
        if not self.raw_data:
            raise NoDevice("No thermostat data available")
        self.homes = {d["id"]: d for d in self.raw_data}
        if not self.homes:
            raise NoDevice("No thermostat available")
        self.modules = {}
        self.rooms = {}
        self.schedules = {}
        self.zones = {}
        self.set_point_duration = {}
        self.default_home = None
        self.default_home_id = None
        for item in self.raw_data:
            id_home = item.get("id")
            if not id_home:
                LOG.error('No key ["id"] in %s', item.keys())
                continue
            home_name = item.get("name")
            if not home_name:
                home_name = "Unknown"
                self.homes[id_home]["name"] = home_name
            if "modules" in item:
                if id_home not in self.modules:
                    self.modules[id_home] = {}
                for module in item["modules"]:
                    self.modules[id_home][module["id"]] = module

                if id_home not in self.rooms:
                    self.rooms[id_home] = {}
                if id_home not in self.schedules:
                    self.schedules[id_home] = {}
                if id_home not in self.zones:
                    self.zones[id_home] = {}
                if id_home not in self.set_point_duration:
                    self.set_point_duration[id_home] = {}
                if "therm_setpoint_default_duration" in item:
                    self.set_point_duration[id_home] = item[
                        "therm_setpoint_default_duration"
                    ]
                if "rooms" in item:
                    for room in item["rooms"]:
                        self.rooms[id_home][room["id"]] = room
                if "therm_schedules" in item:
                    self.default_home = home_name
                    self.default_home_id = item["id"]
                    for schedule in item["therm_schedules"]:
                        self.schedules[id_home][schedule["id"]] = schedule
                    for schedule in item["therm_schedules"]:
                        schedule_id = schedule["id"]
                        if schedule_id not in self.zones[id_home]:
                            self.zones[id_home][schedule_id] = {}
                        for zone in schedule["zones"]:
                            self.zones[id_home][schedule_id][zone["id"]] = zone

    def home_by_id(self, hid):
        return None if hid not in self.homes else self.homes[hid]

    def home_by_name(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                return self.homes[key]
        raise InvalidHome("Invalid Home %s" % home)

    def get_home_id(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                if "therm_schedules" in self.homes[key]:
                    return self.homes[key]["id"]
        raise InvalidHome("Invalid Home %s" % home)

    def get_home_name(self, home_id=None):
        if home_id is None:
            home_id = self.default_home_id

        for key, value in self.homes.items():
            if value["id"] == home_id:
                return self.homes[key]["name"]
        raise InvalidHome("Invalid Home ID %s" % home_id)

    def get_selected_schedule(self, home=None, home_id=None):
        if not home_id:
            if not home:
                home = self.default_home
            home_id = self.get_home_id(home=home)
        return self._get_selected_schedule(home_id=home_id)

    def _get_selected_schedule(self, home_id: str):
        """Get the selected schedule for a given home ID."""
        try:
            schedules = self.schedules[home_id]
        except KeyError:
            raise NoSchedule("No schedules available for %s" % home_id)

        for key in schedules.keys():
            if "selected" in schedules[key].keys():
                return schedules[key]

    def switch_home_schedule(self, schedule_id=None, schedule=None, home=None):
        if home is None:
            home = self.default_home
        home_id = self.get_home_id(home=home)

        schedules = {
            self.schedules[home_id][s]["name"]: self.schedules[home_id][s]["id"]
            for s in self.schedules[home_id]
        }
        if schedule is None and schedule_id is not None:
            if schedule_id not in list(schedules.values()):
                raise NoSchedule("%s is not a valid schedule id" % schedule_id)
        elif schedule_id is None and schedule is not None:
            if schedule not in list(schedules.keys()):
                raise NoSchedule("%s is not a valid schedule" % schedule)
            schedule_id = schedules[schedule]
        else:
            raise NoSchedule("No schedule specified")

        return self._switch_home_schedule(schedule_id=schedule_id, home_id=home_id)

    def _switch_home_schedule(self, schedule_id: str, home_id: str) -> None:
        """."""
        if home_id not in self.schedules:
            raise NoSchedule("No schedules available for %s" % home_id)

        schedules = {
            self.schedules[home_id][s]["name"]: self.schedules[home_id][s]["id"]
            for s in self.schedules[home_id]
        }
        if schedule_id not in list(schedules.values()):
            raise NoSchedule("%s is not a valid schedule id" % schedule_id)

        post_params = {"home_id": home_id, "schedule_id": schedule_id}
        resp = self.auth_data.post_request(
            url=_SWITCHHOMESCHEDULE_REQ, params=post_params
        )
        LOG.debug("Response: %s", resp)


class HomeStatus:
    def __init__(self, auth_data, home_data=None, home_id=None, home=None):
        self.auth_data = auth_data
        if home_data is None:
            self.home_data = HomeData(auth_data)
        else:
            self.home_data = home_data

        if home_id is not None:
            self.home_id = home_id
        elif home is not None:
            self.home_id = self.home_data.get_home_id(home=home)
        else:
            self.home_id = self.home_data.get_home_id(home=self.home_data.default_home)

        post_params = {"home_id": self.home_id}

        resp = self.auth_data.post_request(url=_GETHOMESTATUS_REQ, params=post_params)
        if (
            "errors" in resp
            or "body" not in resp
            or "home" not in resp["body"]
            or ("errors" in resp["body"] and "modules" not in resp["body"]["home"])
        ):
            LOG.error("Errors in response: %s", resp)
            raise NoDevice("No device found, errors in response")
        self.raw_data = resp["body"]["home"]
        self.rooms = {}
        self.thermostats = {}
        self.valves = {}
        self.relays = {}
        for room in self.raw_data.get("rooms", []):
            self.rooms[room["id"]] = room

        for module in self.raw_data.get("modules", []):
            if module["type"] == "NATherm1":
                thermostat_id = module["id"]
                if thermostat_id not in self.thermostats:
                    self.thermostats[thermostat_id] = {}
                self.thermostats[thermostat_id] = module
            elif module["type"] == "NRV":
                valve_id = module["id"]
                if valve_id not in self.valves:
                    self.valves[valve_id] = {}
                self.valves[valve_id] = module
            elif module["type"] == "NAPlug":
                relay_id = module["id"]
                if relay_id not in self.relays:
                    self.relays[relay_id] = {}
                self.relays[relay_id] = module
        if self.rooms != {}:
            self.default_room = list(self.rooms.values())[0]
        if self.relays != {}:
            self.default_relay = list(self.relays.values())[0]
        if self.thermostats != {}:
            self.default_thermostat = list(self.thermostats.values())[0]
        if self.valves != {}:
            self.default_valve = list(self.valves.values())[0]

    def room_by_id(self, rid):
        if not rid:
            return self.default_room
        for key, value in self.rooms.items():
            if value["id"] == rid:
                return self.rooms[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def thermostat_by_id(self, rid):
        if not rid:
            return self.default_thermostat
        for key, value in self.thermostats.items():
            if value["id"] == rid:
                return self.thermostats[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def relay_by_id(self, rid):
        if not rid:
            return self.default_relay
        for key, value in self.relays.items():
            if value["id"] == rid:
                return self.relays[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def valve_by_id(self, rid):
        if not rid:
            return self.default_valve
        for key, value in self.valves.items():
            if value["id"] == rid:
                return self.valves[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def set_point(self, rid=None):
        """
        Return the setpoint of a given room.
        """
        setpoint = None
        room_data = self.room_by_id(rid=rid)
        if room_data:
            setpoint = room_data["therm_setpoint_temperature"]
        return setpoint

    def set_point_mode(self, rid=None):
        """
        Return the setpointmode of a given room.
        """
        setpointmode = None
        try:
            room_data = self.room_by_id(rid=rid)
        except InvalidRoom:
            LOG.debug("Invalid room %s", rid)
            room_data = None
        if room_data:
            setpointmode = room_data["therm_setpoint_mode"]
        return setpointmode

    def get_away_temp(self, home=None, home_id=None):
        if not home_id:
            if not home:
                home = self.home_data.default_home
            try:
                home_id = self.home_data.get_home_id(home)
            except InvalidHome:
                LOG.debug("No Schedule for Home ID %s", home_id)
                return None
        try:
            data = self.home_data.get_selected_schedule(home_id=home_id)
        except NoSchedule:
            LOG.debug("No Schedule for Home ID %s", home_id)
            return None
        return data["away_temp"]

    def get_hg_temp(self, home=None, home_id=None):
        if not home_id:
            if not home:
                home = self.home_data.default_home
            home_id = self.home_data.get_home_id(home)
        try:
            data = self.home_data.get_selected_schedule(home_id=home_id)
        except NoSchedule:
            LOG.debug("No Schedule for Home ID %s", home_id)
            return None
        return data["hg_temp"]

    def measured_temperature(self, rid=None):
        """
        Return the measured temperature of a given room.
        """
        temperature = None
        room_data = self.room_by_id(rid=rid)
        if room_data:
            temperature = room_data.get("therm_measured_temperature")
        return temperature

    def boiler_status(self, rid=None):
        boiler_status = None
        if rid:
            relay_status = self.thermostat_by_id(rid=rid)
        else:
            relay_status = self.thermostat_by_id(rid=None)
        if relay_status:
            boiler_status = relay_status["boiler_status"]
        return boiler_status

    def thermostat_type(self, home, rid, home_id=None):
        if home_id is None:
            home_id = self.home_data.get_home_id(home=home)
        for key in self.home_data.rooms[home_id]:
            if key == rid:
                for module_id in self.home_data.rooms[home_id][rid]["module_ids"]:
                    if module_id in self.thermostats:
                        return "NATherm1"
                    if module_id in self.valves:
                        return "NRV"

    def set_therm_mode(self, home_id, mode, end_time=None, schedule_id=None):
        post_params = {
            "home_id": home_id,
            "mode": mode,
        }
        if end_time is not None and mode in ("hg", "away"):
            post_params["endtime"] = end_time
        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id
        return self.auth_data.post_request(url=_SETTHERMMODE_REQ, params=post_params)

    def set_room_therm_point(self, home_id, room_id, mode, temp=None, end_time=None):
        post_params = {
            "home_id": home_id,
            "room_id": room_id,
            "mode": mode,
        }
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            post_params["temp"] = temp
        if end_time is not None:
            post_params["endtime"] = end_time
        return self.auth_data.post_request(
            url=_SETROOMTHERMPOINT_REQ, params=post_params
        )
