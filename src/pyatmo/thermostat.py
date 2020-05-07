import logging

from .exceptions import InvalidHome, InvalidRoom, NoDevice, NoSchedule
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
    List the Energy devices (relays, thermostat modules and valves)

    Args:
        authData (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, authData):
        self.authData = authData
        resp = self.authData.post_request(url=_GETHOMESDATA_REQ)
        if resp is None or "body" not in resp:
            raise NoDevice("No thermostat data returned by Netatmo server")
        self.rawData = resp["body"].get("homes")
        if not self.rawData:
            raise NoDevice("No thermostat data available")
        self.homes = {d["id"]: d for d in self.rawData}
        if not self.homes:
            raise NoDevice("No thermostat available")
        self.modules = {}
        self.rooms = {}
        self.schedules = {}
        self.zones = {}
        self.setpoint_duration = {}
        self.default_home = None
        self.default_home_id = None
        for item in self.rawData:
            idHome = item.get("id")
            if not idHome:
                LOG.error('No key ["id"] in %s', item.keys())
                continue
            nameHome = item.get("name")
            if not nameHome:
                nameHome = "Unknown"
                self.homes[idHome]["name"] = nameHome
            if "modules" in item:
                if idHome not in self.modules:
                    self.modules[idHome] = {}
                for m in item["modules"]:
                    self.modules[idHome][m["id"]] = m
                if idHome not in self.rooms:
                    self.rooms[idHome] = {}
                if idHome not in self.schedules:
                    self.schedules[idHome] = {}
                if idHome not in self.zones:
                    self.zones[idHome] = {}
                if idHome not in self.setpoint_duration:
                    self.setpoint_duration[idHome] = {}
                if "therm_setpoint_default_duration" in item:
                    self.setpoint_duration[idHome] = item[
                        "therm_setpoint_default_duration"
                    ]
                if "rooms" in item:
                    for room in item["rooms"]:
                        self.rooms[idHome][room["id"]] = room
                if "therm_schedules" in item:
                    self.default_home = nameHome
                    self.default_home_id = item["id"]
                    for schedule in item["therm_schedules"]:
                        self.schedules[idHome][schedule["id"]] = schedule
                    for schedule in item["therm_schedules"]:
                        scheduleId = schedule["id"]
                        if scheduleId not in self.zones[idHome]:
                            self.zones[idHome][scheduleId] = {}
                        for zone in schedule["zones"]:
                            self.zones[idHome][scheduleId][zone["id"]] = zone

    def homeById(self, hid):
        return None if hid not in self.homes else self.homes[hid]

    def homeByName(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                return self.homes[key]
        raise InvalidHome("Invalid Home %s" % home)

    def gethomeId(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                if "therm_schedules" in self.homes[key]:
                    return self.homes[key]["id"]
        raise InvalidHome("Invalid Home %s" % home)

    def getHomeName(self, home_id=None):
        if home_id is None:
            home_id = self.default_home_id
        for key, value in self.homes.items():
            if value["id"] == home_id:
                return self.homes[key]["name"]
        raise InvalidHome("Invalid Home ID %s" % home_id)

    def getSelectedschedule(self, home=None, home_id=None):
        if not home_id:
            if not home:
                home = self.default_home
            home_id = self.gethomeId(home=home)
        return self.get_selected_schedule(home_id=home_id)

    def get_selected_schedule(self, home_id: str):
        """Get the selected schedule for a given home ID."""
        try:
            schedules = self.schedules[home_id]
        except KeyError:
            raise NoSchedule("No schedules available for %s" % home_id)

        for key in schedules.keys():
            if "selected" in schedules[key].keys():
                return schedules[key]

    def switchHomeSchedule(self, schedule_id=None, schedule=None, home=None):
        if home is None:
            home = self.default_home
        home_id = self.gethomeId(home=home)

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

        return self.switch_home_schedule(schedule_id=schedule_id, home_id=home_id)

    def switch_home_schedule(self, schedule_id: str, home_id: str) -> bool:
        """."""
        try:
            schedules = self.schedules[home_id]
        except KeyError:
            raise NoSchedule("No schedules available for %s" % home_id)

        schedules = {
            self.schedules[home_id][s]["name"]: self.schedules[home_id][s]["id"]
            for s in self.schedules[home_id]
        }
        if schedule_id not in list(schedules.values()):
            raise NoSchedule("%s is not a valid schedule id" % schedule_id)

        postParams = {
            "home_id": home_id,
            "schedule_id": schedule_id,
        }
        resp = self.authData.post_request(
            url=_SWITCHHOMESCHEDULE_REQ, params=postParams
        )
        LOG.debug("Response: %s", resp)


class HomeStatus:
    def __init__(self, authData, home_data=None, home_id=None, home=None):
        self.authData = authData
        if home_data is None:
            self.home_data = HomeData(authData)
        else:
            self.home_data = home_data

        if home_id is not None:
            self.home_id = home_id
        elif home is not None:
            self.home_id = self.home_data.gethomeId(home=home)
        else:
            self.home_id = self.home_data.gethomeId(home=self.home_data.default_home)
        postParams = {"home_id": self.home_id}

        resp = self.authData.post_request(url=_GETHOMESTATUS_REQ, params=postParams)
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
        if self.rooms != {}:
            self.default_room = list(self.rooms.values())[0]
        if self.relays != {}:
            self.default_relay = list(self.relays.values())[0]
        if self.thermostats != {}:
            self.default_thermostat = list(self.thermostats.values())[0]
        if self.valves != {}:
            self.default_valve = list(self.valves.values())[0]

    def roomById(self, rid):
        if not rid:
            return self.default_room
        for key, value in self.rooms.items():
            if value["id"] == rid:
                return self.rooms[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def thermostatById(self, rid):
        if not rid:
            return self.default_thermostat
        for key, value in self.thermostats.items():
            if value["id"] == rid:
                return self.thermostats[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def relayById(self, rid):
        if not rid:
            return self.default_relay
        for key, value in self.relays.items():
            if value["id"] == rid:
                return self.relays[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def valveById(self, rid):
        if not rid:
            return self.default_valve
        for key, value in self.valves.items():
            if value["id"] == rid:
                return self.valves[key]
        raise InvalidRoom("No room with ID %s" % rid)

    def setPoint(self, rid=None):
        """
        Return the setpoint of a given room.
        """
        setpoint = None
        room_data = self.roomById(rid=rid)
        if room_data:
            setpoint = room_data["therm_setpoint_temperature"]
        return setpoint

    def setPointmode(self, rid=None):
        """
        Return the setpointmode of a given room.
        """
        setpointmode = None
        try:
            room_data = self.roomById(rid=rid)
        except InvalidRoom:
            LOG.debug("Invalid room %s", rid)
            room_data = None
        if room_data:
            setpointmode = room_data["therm_setpoint_mode"]
        return setpointmode

    def getAwaytemp(self, home=None, home_id=None):
        if not home_id:
            if not home:
                home = self.home_data.default_home
            try:
                home_id = self.home_data.gethomeId(home)
            except InvalidHome:
                LOG.debug("No Schedule for Home ID %s", home_id)
                return None
        try:
            data = self.home_data.getSelectedschedule(home_id=home_id)
        except NoSchedule:
            LOG.debug("No Schedule for Home ID %s", home_id)
            return None
        return data["away_temp"]

    def getHgtemp(self, home=None, home_id=None):
        if not home_id:
            if not home:
                home = self.home_data.default_home
            home_id = self.home_data.gethomeId(home)
        try:
            data = self.home_data.getSelectedschedule(home_id=home_id)
        except NoSchedule:
            LOG.debug("No Schedule for Home ID %s", home_id)
            return None
        return data["hg_temp"]

    def measuredTemperature(self, rid=None):
        """
        Return the measured temperature of a given room.
        """
        temperature = None
        room_data = self.roomById(rid=rid)
        if room_data:
            temperature = room_data.get("therm_measured_temperature")
        return temperature

    def boilerStatus(self, rid=None):
        boiler_status = None
        if rid:
            relay_status = self.thermostatById(rid=rid)
        else:
            relay_status = self.thermostatById(rid=None)
        if relay_status:
            boiler_status = relay_status["boiler_status"]
        return boiler_status

    def thermostatType(self, home, rid, home_id=None):
        module_id = None
        if home_id is None:
            home_id = self.home_data.gethomeId(home=home)
        for key in self.home_data.rooms[home_id]:
            if key == rid:
                for module_id in self.home_data.rooms[home_id][rid]["module_ids"]:
                    if module_id in self.thermostats:
                        return "NATherm1"
                    if module_id in self.valves:
                        return "NRV"

    def setThermmode(self, home_id, mode, end_time=None, schedule_id=None):
        postParams = {
            "home_id": home_id,
            "mode": mode,
        }
        if end_time is not None and mode in ("hg", "away"):
            postParams["endtime"] = end_time
        if schedule_id is not None and mode == "schedule":
            postParams["schedule_id"] = schedule_id
        return self.authData.post_request(url=_SETTHERMMODE_REQ, params=postParams)

    def setroomThermpoint(self, home_id, room_id, mode, temp=None, end_time=None):
        postParams = {
            "home_id": home_id,
            "room_id": room_id,
            "mode": mode,
        }
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            postParams["temp"] = temp
        if end_time is not None:
            postParams["endtime"] = end_time
        return self.authData.post_request(url=_SETROOMTHERMPOINT_REQ, params=postParams)
