import logging
import time

from . import _BASE_URL, postRequest, todayStamps
from .Exceptions import NoDevice

LOG = logging.getLogger(__name__)

_GETMEASURE_REQ = _BASE_URL + "api/getmeasure"
_GETSTATIONDATA_REQ = _BASE_URL + "api/getstationsdata"


class WeatherStationData:
    """
    List the Weather Station devices (stations and modules)
    Args:
        authData (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, authData, urlReq=None):
        self.urlReq = urlReq or _GETSTATIONDATA_REQ
        self.getAuthToken = authData.accessToken
        postParams = {"access_token": self.getAuthToken}
        resp = postRequest(self.urlReq, postParams)
        if resp is None:
            raise NoDevice("No weather station data returned by Netatmo server")
        try:
            self.rawData = resp["body"].get("devices")
        except KeyError:
            LOG.debug("No <body> in response %s", resp)
            raise NoDevice("No weather station data returned by Netatmo server")
        if not self.rawData:
            raise NoDevice("No weather station available")
        self.stations = {d["_id"]: d for d in self.rawData}
        self.modules = {}
        for item in self.rawData:
            if "modules" not in item:
                item["modules"] = [item]
            for m in item["modules"]:
                if "module_name" not in m:
                    if m["type"] == "NHC":
                        m["module_name"] = m["station_name"]
                    else:
                        continue
                self.modules[m["_id"]] = m
                self.modules[m["_id"]]["main_device"] = item["_id"]
        self.default_station = list(self.stations.values())[0]["station_name"]

    def modulesNamesList(self, station=None, station_id=None):
        res = set()
        station_data = None
        if station_id is not None:
            station_data = self.stationById(station_id)
        elif station is not None:
            station_data = self.stationByName(station)
        if station_data is not None:
            res.add(station_data["module_name"])
            for m in station_data["modules"]:
                res.add(m["module_name"])
        else:
            res.update([m["module_name"] for m in self.modules.values()])
            for id, station in self.stations.items():
                res.add(station["module_name"])
        return list(res)

    def stationByName(self, station=None):
        if not station:
            station = self.default_station
        for i, s in self.stations.items():
            if s["station_name"] == station:
                return self.stations[i]
        return None

    def stationById(self, sid):
        return None if sid not in self.stations else self.stations[sid]

    def moduleByName(self, module, station=None):
        s = None
        if station:
            s = self.stationByName(station)
            if not s:
                return None
            elif s["module_name"] == module:
                return s
        else:
            for id, station in self.stations.items():
                if "module_name" in station and station["module_name"] == module:
                    return station
        for m in self.modules:
            mod = self.modules[m]
            if mod["module_name"] == module:
                if not s or mod["main_device"] == s["_id"]:
                    return mod
        return None

    def moduleById(self, mid, sid=None):
        s = self.stationById(sid) if sid else None
        if mid in self.modules:
            if s:
                for module in s["modules"]:
                    if module["_id"] == mid:
                        return module
            else:
                return self.modules[mid]

    def monitoredConditions(self, module):
        mod = self.moduleByName(module)
        conditions = []
        for cond in mod["data_type"]:
            if cond == "Wind":
                # the Wind meter actually exposes the following conditions
                conditions.extend(
                    ["windangle", "windstrength", "gustangle", "guststrength"]
                )
            elif cond == "Rain":
                conditions.extend(["Rain", "sum_rain_24", "sum_rain_1"])
            else:
                conditions.append(cond.lower())
        if mod["type"] == "NAMain" or mod["type"] == "NHC":
            # the main module has wifi_status
            conditions.append("wifi_status")
        else:
            # assume all other modules have rf_status, battery_vp, and battery_percent
            conditions.extend(["rf_status", "battery_vp", "battery_percent"])
        if (
            mod["type"] == "NAMain"
            or mod["type"] == "NHC"
            or mod["type"] == "NAModule1"
            or mod["type"] == "NAModule4"
        ):
            conditions.extend(["min_temp", "max_temp"])
        return conditions

    def lastData(self, station=None, exclude=0):
        if station is not None:
            stations = [station]
        else:
            stations = [s["station_name"] for s in list(self.stations.values())]
        # Breaking change from Netatmo : dashboard_data no longer available if station lost
        lastD = {}
        for st in stations:
            s = self.stationByName(st)
            if not s or "dashboard_data" not in s:
                return None
            # Define oldest acceptable sensor measure event
            limit = (time.time() - exclude) if exclude else 0
            ds = s["dashboard_data"]
            if "module_name" in s and ds["time_utc"] > limit:
                lastD[s["module_name"]] = ds.copy()
                lastD[s["module_name"]]["When"] = lastD[s["module_name"]].pop(
                    "time_utc"
                )
                lastD[s["module_name"]]["wifi_status"] = s["wifi_status"]
            for module in s["modules"]:
                if "dashboard_data" not in module or "module_name" not in module:
                    continue
                ds = module["dashboard_data"]
                if "time_utc" in ds and ds["time_utc"] > limit:
                    lastD[module["module_name"]] = ds.copy()
                    lastD[module["module_name"]]["When"] = lastD[
                        module["module_name"]
                    ].pop("time_utc")
                    # For potential use, add battery and radio coverage information to module data if present
                    for i in (
                        "rf_status",
                        "battery_vp",
                        "battery_percent",
                        "wifi_status",
                    ):
                        if i in module:
                            lastD[module["module_name"]][i] = module[i]
        return lastD

    def checkNotUpdated(self, station=None, delay=3600):
        res = self.lastData(station)
        ret = []
        for mn, v in res.items():
            if time.time() - v["When"] > delay:
                ret.append(mn)
        return ret if ret else None

    def checkUpdated(self, station=None, delay=3600):
        res = self.lastData(station)
        ret = []
        for mn, v in res.items():
            if time.time() - v["When"] < delay:
                ret.append(mn)
        return ret if ret else None

    def getMeasure(
        self,
        device_id,
        scale,
        mtype,
        module_id=None,
        date_begin=None,
        date_end=None,
        limit=None,
        optimize=False,
        real_time=False,
    ):
        postParams = {"access_token": self.getAuthToken}
        postParams["device_id"] = device_id
        if module_id:
            postParams["module_id"] = module_id
        postParams["scale"] = scale
        postParams["type"] = mtype
        if date_begin:
            postParams["date_begin"] = date_begin
        if date_end:
            postParams["date_end"] = date_end
        if limit:
            postParams["limit"] = limit
        postParams["optimize"] = "true" if optimize else "false"
        postParams["real_time"] = "true" if real_time else "false"
        return postRequest(_GETMEASURE_REQ, postParams)

    def MinMaxTH(self, station=None, module=None, frame="last24"):
        if not station:
            station = self.default_station
        s = self.stationByName(station)
        if not s:
            s = self.stationById(station)
            if not s:
                return None
        if frame == "last24":
            end = time.time()
            start = end - 24 * 3600  # 24 hours ago
        elif frame == "day":
            start, end = todayStamps()
        if module and module != s["module_name"]:
            m = self.moduleByName(module, s["station_name"])
            if not m:
                m = self.moduleById(s["_id"], module)
                if not m:
                    return None
            # retrieve module's data
            resp = self.getMeasure(
                device_id=s["_id"],
                module_id=m["_id"],
                scale="max",
                mtype="Temperature,Humidity",
                date_begin=start,
                date_end=end,
            )
        else:  # retrieve station's data
            resp = self.getMeasure(
                device_id=s["_id"],
                scale="max",
                mtype="Temperature,Humidity",
                date_begin=start,
                date_end=end,
            )
        if resp:
            T = [v[0] for v in resp["body"].values()]
            H = [v[1] for v in resp["body"].values()]
            return min(T), max(T), min(H), max(H)
        else:
            return None
