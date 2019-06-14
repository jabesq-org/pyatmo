import logging

from . import _BASE_URL, NoDevice, postRequest

LOG = logging.getLogger(__name__)

_GETHOMESDATA_REQ = _BASE_URL + "api/homesdata"
_GETHOMESTATUS_REQ = _BASE_URL + "api/homestatus"
_SETTHERMMODE_REQ = _BASE_URL + "api/setthermmode"
_SETROOMTHERMPOINT_REQ = _BASE_URL + "api/setroomthermpoint"
_GETROOMMEASURE_REQ = _BASE_URL + "api/getroommeasure"
_SWITCHHOMESCHEDULE_REQ = _BASE_URL + "api/switchhomeschedule"


class NoSchedule(Exception):
    pass


class HomeData:
    """
    List the Energy devices (relays, thermostat modules and valves)

    Args:
        authData (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, authData):
        self.getAuthToken = authData.accessToken
        postParams = {"access_token": self.getAuthToken}
        resp = postRequest(_GETHOMESDATA_REQ, postParams)
        if resp is None:
            raise NoDevice("No thermostat data returned by Netatmo server")
        self.rawData = resp["body"].get("homes")
        if not self.rawData:
            raise NoDevice("No thermostat data available")
        self.homes = {d["id"]: d for d in self.rawData}
        if not self.homes:
            raise NoDevice("No thermostat available")
        self.modules = dict()
        self.rooms = dict()
        self.schedules = dict()
        self.zones = dict()
        self.setpoint_duration = dict()
        for i in range(len(self.rawData)):
            nameHome = self.rawData[i].get("name")
            if not nameHome:
                raise NoDevice('No key ["name"] in %s', self.rawData[i].keys())
            if "modules" in self.rawData[i]:
                if nameHome not in self.modules:
                    self.modules[nameHome] = dict()
                for m in self.rawData[i]["modules"]:
                    self.modules[nameHome][m["id"]] = m
                if nameHome not in self.rooms:
                    self.rooms[nameHome] = dict()
                if nameHome not in self.schedules:
                    self.schedules[nameHome] = dict()
                if nameHome not in self.zones:
                    self.zones[nameHome] = dict()
                if nameHome not in self.setpoint_duration:
                    self.setpoint_duration[nameHome] = dict()
                if "therm_setpoint_default_duration" in self.rawData[i]:
                    self.setpoint_duration[nameHome] = self.rawData[i][
                        "therm_setpoint_default_duration"
                    ]
                if "rooms" in self.rawData[i]:
                    for r in self.rawData[i]["rooms"]:
                        self.rooms[nameHome][r["id"]] = r
                if "therm_schedules" in self.rawData[i]:
                    self.default_home = self.rawData[i]["name"]
                    for s in self.rawData[i]["therm_schedules"]:
                        self.schedules[nameHome][s["id"]] = s
                    for t in range(len(self.rawData[i]["therm_schedules"])):
                        idSchedule = self.rawData[i]["therm_schedules"][t]["id"]
                        if idSchedule not in self.zones[nameHome]:
                            self.zones[nameHome][idSchedule] = dict()
                        for z in self.rawData[i]["therm_schedules"][t]["zones"]:
                            self.zones[nameHome][idSchedule][z["id"]] = z

    def homeById(self, hid):
        return None if hid not in self.homes else self.homes[hid]

    def homeByName(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                return self.homes[key]

    def gethomeId(self, home=None):
        if not home:
            home = self.default_home
        for key, value in self.homes.items():
            if value["name"] == home:
                LOG.debug(self.homes[key]["id"])
                LOG.debug(self.default_home)
                if "therm_schedules" in self.homes[key]:
                    return self.homes[key]["id"]

    def getSelectedschedule(self, home=None):
        if not home:
            home = self.default_home
        self.schedule = self.schedules[home]
        for key in self.schedule.keys():
            if "selected" in self.schedule[key].keys():
                return self.schedule[key]

    def switchHomeSchedule(self, schedule_id=None, schedule=None, home=None):
        if home is None:
            home = self.default_home
        home_id = self.gethomeId(home=home)
        schedules = {
            self.schedules[home][s]["name"]: self.schedules[home][s]["id"]
            for s in self.schedules[home]
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
        postParams = {
            "access_token": self.getAuthToken,
            "home_id": home_id,
            "schedule_id": schedule_id,
        }
        resp = postRequest(_SWITCHHOMESCHEDULE_REQ, postParams)
        LOG.debug("Response: %s", resp)


class HomeStatus(HomeData):
    """
    """

    def __init__(self, authData, home_id=None, home=None):
        self.getAuthToken = authData.accessToken
        # print(self.modules())
        self.home_data = HomeData(authData)
        # print(home_data.modules)
        if home_id:
            self.home_id = home_id
            LOG.debug("home_id", self.home_id)
        elif home:
            self.home_id = self.home_data.gethomeId(home=home)
        else:
            self.home_id = self.home_data.gethomeId(home=self.home_data.default_home)
        postParams = {"access_token": self.getAuthToken, "home_id": self.home_id}

        resp = postRequest(_GETHOMESTATUS_REQ, postParams)
        if (
            "body" in resp
            and "errors" in resp["body"]
            or "body" not in resp
            or "home" not in resp["body"]
        ):
            raise NoDevice("No device found, errors in response")
            return None
        self.rawData = resp["body"]["home"]
        self.rooms = dict()
        self.thermostats = dict()
        self.valves = dict()
        self.relays = dict()
        for r in self.rawData["rooms"]:
            self.rooms[r["id"]] = r
        for t in range(len(self.rawData["modules"])):
            if self.rawData["modules"][t]["type"] == "NATherm1":
                thermostatId = self.rawData["modules"][t]["id"]
                if thermostatId not in self.thermostats:
                    self.thermostats[thermostatId] = dict()
                self.thermostats[thermostatId] = self.rawData["modules"][t]
            # self.thermostats[t['id']] = t
        for v in range(len(self.rawData["modules"])):
            if self.rawData["modules"][v]["type"] == "NRV":
                valveId = self.rawData["modules"][v]["id"]
                if valveId not in self.valves:
                    self.valves[valveId] = dict()
                self.valves[valveId] = self.rawData["modules"][v]
        for r in range(len(self.rawData["modules"])):
            if self.rawData["modules"][r]["type"] == "NAPlug":
                relayId = self.rawData["modules"][r]["id"]
                if relayId not in self.relays:
                    self.relays[relayId] = dict()
                self.relays[relayId] = self.rawData["modules"][r]
        if self.rooms != {}:
            self.default_room = list(self.rooms.values())[0]
        if self.relays != {}:
            self.default_relay = list(self.relays.values())[0]
        if self.thermostats != {}:
            self.default_thermostat = list(self.thermostats.values())[0]
        LOG.debug(self.thermostats)
        if self.valves != {}:
            self.default_valve = list(self.valves.values())[0]

    def roomById(self, rid):
        if not rid:
            return self.default_room
        for key, value in self.rooms.items():
            if value["id"] == rid:
                return self.rooms[key]

    def thermostatById(self, rid):
        if not rid:
            return self.default_thermostat
        for key, value in self.thermostats.items():
            if value["id"] == rid:
                return self.thermostats[key]

    def relayById(self, rid):
        if not rid:
            return self.default_relay
        for key, value in self.relays.items():
            if value["id"] == rid:
                return self.relays[key]

    def valveById(self, rid):
        if not rid:
            return self.default_valve
        for key, value in self.valves.items():
            if value["id"] == rid:
                return self.valves[key]

    def setPoint(self, rid=None):
        """
        Return the setpoint of a given room.
        """
        setpoint = None
        if rid:
            room_data = self.roomById(rid=rid)
        else:
            room_data = self.roomById(rid=None)
        if room_data:
            setpoint = room_data["therm_setpoint_temperature"]
        return setpoint

    def setPointmode(self, rid=None):
        """
        Return the setpointmode of a given room.
        """
        setpointmode = None
        if rid:
            room_data = self.roomById(rid=rid)
        else:
            room_data = self.roomById(rid=None)
        if room_data:
            setpointmode = room_data["therm_setpoint_mode"]
        return setpointmode

    def getAwaytemp(self, home=None):
        if not home:
            home = self.home_data.default_home
            LOG.debug(self.home_data.default_home)
        data = self.home_data.getSelectedschedule(home=home)
        return data["away_temp"]

    def getHgtemp(self, home=None):
        if not home:
            home = self.home_data.default_home
        data = self.home_data.getSelectedschedule(home=home)
        return data["hg_temp"]

    def measuredTemperature(self, rid=None):
        """
        Return the measured temperature of a given room.
        """
        temperature = None
        LOG.debug(rid)
        if rid:
            room_data = self.roomById(rid=rid)
        else:
            room_data = self.roomById(rid=None)
        if room_data:
            temperature = room_data["therm_measured_temperature"]
        return temperature

    def boilerStatus(self, rid=None):
        boiler_status = None
        LOG.debug(rid)
        if rid:
            relay_status = self.thermostatById(rid=rid)
        else:
            relay_status = self.thermostatById(rid=None)
        if relay_status:
            boiler_status = relay_status["boiler_status"]
        return boiler_status

    def thermostatType(self, home, rid):
        module_id = None
        for key in self.home_data.rooms[home]:
            if key == rid:
                for module_id in self.home_data.rooms[home][rid]["module_ids"]:
                    self.module_id = module_id
                    if module_id in self.thermostats:
                        return "NATherm1"
                    if module_id in self.valves:
                        return "NRV"

    def setThermmode(self, home_id, mode):
        postParams = {
            "access_token": self.getAuthToken,
            "home_id": home_id,
            "mode": mode,
        }
        resp = postRequest(_SETTHERMMODE_REQ, postParams)
        LOG.debug(resp)

    def setroomThermpoint(self, home_id, room_id, mode, temp=None):
        postParams = {
            "access_token": self.getAuthToken,
            "home_id": home_id,
            "room_id": room_id,
            "mode": mode,
        }
        if temp is not None:
            postParams["temp"] = temp
        return postRequest(_SETROOMTHERMPOINT_REQ, postParams)
