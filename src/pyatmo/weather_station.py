import logging
import time
from typing import Dict, List

from .exceptions import NoDevice
from .helpers import _BASE_URL, fixId, todayStamps

LOG = logging.getLogger(__name__)

_GETMEASURE_REQ = _BASE_URL + "api/getmeasure"
_GETSTATIONDATA_REQ = _BASE_URL + "api/getstationsdata"


class WeatherStationData:
    """
    List the Weather Station devices (stations and modules)
    Args:
        auth_data (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, auth_data, url_req: str = None):
        """Initialize the weather station class."""
        self.url_req = url_req or _GETSTATIONDATA_REQ
        self.auth_data = auth_data

        resp = self.auth_data.post_request(url=self.url_req)

        if resp is None or "body" not in resp:
            raise NoDevice("No weather station data returned by Netatmo server")
        try:
            self.rawData = fixId(resp["body"].get("devices"))
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

    def get_module_names(self, station_id: str) -> List:
        """Return a list of all module names for a given or all stations."""
        res = set()
        station_data = self.get_station(station_id)
        print(station_data)

        if not station_data:
            return []

        res.add(station_data.get("module_name", station_data.get("type")))
        for m in station_data["modules"]:
            # Add module name, use module type if no name is available
            res.add(m.get("module_name", m.get("type")))

        return list(res)

    def get_modules(self, station_id: str) -> Dict:
        """Return a dict of modules for a given or all stations."""
        station_data = self.get_station(station_id)

        if not station_data:
            return {}

        res = {}
        for station in [self.stations[station_data["_id"]]]:
            res[station["_id"]] = {
                "station_name": station["station_name"],
                "module_name": station.get("module_name", station.get("type")),
                "id": station["_id"],
            }

            for module in station["modules"]:
                res[module["_id"]] = {
                    "station_name": module.get("station_name", station["station_name"]),
                    "module_name": module.get("module_name", module.get("type")),
                    "id": module["_id"],
                }
        return res

    def get_station(self, station_id: str) -> Dict:
        """Return station by id."""
        return self.stations.get(station_id, {})

    def get_module(self, mid, sid=None):
        """Return module by id."""
        station = self.get_station(sid) if sid else None
        if mid in self.modules:
            if station:
                for module in station["modules"]:
                    if module["_id"] == mid:
                        return module
            else:
                return self.modules[mid]
        return {}

    def get_monitored_conditions(self, module_id: str) -> List:
        """Return monitored conditions for given module(s)."""
        module = self.get_module(module_id)
        if not module:
            module = self.get_station(module_id)

        if not module:
            return []

        conditions = []
        for condition in module.get("data_type", []):
            if condition == "Wind":
                # the Wind meter actually exposes the following conditions
                conditions.extend(
                    ["WindAngle", "WindStrength", "GustAngle", "GustStrength"]
                )
            elif condition == "Rain":
                conditions.extend(["Rain", "sum_rain_24", "sum_rain_1"])
            else:
                conditions.append(condition)
        if module["type"] in ["NAMain", "NHC"]:
            # the main module has wifi_status
            conditions.append("wifi_status")
        else:
            # assume all other modules have rf_status, battery_vp, and battery_percent
            conditions.extend(["rf_status", "battery_vp", "battery_percent"])
        if module["type"] in ["NAMain", "NAModule1", "NAModule4", "NHC"]:
            conditions.extend(["min_temp", "max_temp"])
        if module["type"] in [
            "NAMain",
            "NAModule1",
            "NAModule2",
            "NAModule3",
            "NAModule4",
            "NHC",
        ]:
            conditions.append("reachable")
        return conditions

    def get_last_data(self, station_id=None, exclude=0):
        """Return data for a given station and time frame."""
        key = "_id"

        # Breaking change from Netatmo : dashboard_data no longer available if station lost
        lastD = {}
        s = self.get_station(station_id)

        if not s or "dashboard_data" not in s:
            LOG.debug("No dashboard data for station %s", station_id)
            return lastD

        # Define oldest acceptable sensor measure event
        limit = (time.time() - exclude) if exclude else 0

        ds = s["dashboard_data"]
        if key in s and ds["time_utc"] > limit:
            lastD[s[key]] = ds.copy()
            lastD[s[key]]["When"] = lastD[s[key]].pop("time_utc")
            lastD[s[key]]["wifi_status"] = s["wifi_status"]
            lastD[s[key]]["reachable"] = s["reachable"]

        for module in s["modules"]:

            if "dashboard_data" not in module or key not in module:
                continue

            ds = module["dashboard_data"]
            if "time_utc" in ds and ds["time_utc"] > limit:
                lastD[module[key]] = ds.copy()
                lastD[module[key]]["When"] = lastD[module[key]].pop("time_utc")

                # For potential use, add battery and radio coverage information to module data if present
                for i in (
                    "rf_status",
                    "battery_vp",
                    "battery_percent",
                    "reachable",
                    "wifi_status",
                ):
                    if i in module:
                        lastD[module[key]][i] = module[i]

        return lastD

    def check_not_updated(self, station_id: str, delay: int = 3600):
        """Check if a given station has not been updated."""
        res = self.get_last_data(station_id)
        ret = []
        for mn, v in res.items():
            if time.time() - v["When"] > delay:
                ret.append(mn)
        return ret

    def check_updated(self, station_id: str, delay: int = 3600):
        """Check if a given station has been updated."""
        res = self.get_last_data(station_id)
        ret = []
        for mn, v in res.items():
            if time.time() - v["When"] < delay:
                ret.append(mn)
        return ret

    def get_measure(
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
        """Retrieve data from a device or module."""
        postParams = {"device_id": device_id}
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

        return self.auth_data.post_request(url=_GETMEASURE_REQ, params=postParams)

    def get_min_max_t_h(
        self, station_id: str, module_id: str = None, frame: str = "last24"
    ):
        """Return minimum and maximum temperature and humidity over the given timeframe.

        Arguments:
            station_id {str} -- Station ID

        Keyword Arguments:
            module_id {str} -- Module ID (default: {None})
            frame {str} -- Timeframe can be "last24" or "day" (default: {"last24"})

        Returns:
            (min_t {float}, max_t {float}, min_h {float}, max_h {float}) -- minimum and maximum for temperature and humidity
        """
        if frame == "last24":
            end = time.time()
            start = end - 24 * 3600  # 24 hours ago
        elif frame == "day":
            start, end = todayStamps()

        resp = self.get_measure(
            device_id=station_id,
            module_id=module_id,
            scale="max",
            mtype="Temperature,Humidity",
            date_begin=start,
            date_end=end,
        )

        if resp:
            T = [v[0] for v in resp["body"].values()]
            H = [v[1] for v in resp["body"].values()]
            return min(T), max(T), min(H), max(H)
