import logging
import time

from pyatmo.exceptions import NoDevice
from pyatmo.helpers import BASE_URL, fix_id, today_stamps

LOG = logging.getLogger(__name__)

_GETMEASURE_REQ = BASE_URL + "api/getmeasure"
_GETSTATIONDATA_REQ = BASE_URL + "api/getstationsdata"


class WeatherStationData:
    """
    List the Weather Station devices (stations and modules)
    Args:
        auth_data (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, auth_data, url_req=None):
        """Initialize the weather station class."""
        self.url_req = url_req or _GETSTATIONDATA_REQ
        self.auth_data = auth_data

        resp = self.auth_data.post_request(url=self.url_req)
        if resp is None or "body" not in resp:
            raise NoDevice("No weather station data returned by Netatmo server")
        try:
            self.raw_data = fix_id(resp["body"].get("devices"))
        except KeyError:
            LOG.debug("No <body> in response %s", resp)
            raise NoDevice("No weather station data returned by Netatmo server")

        if not self.raw_data:
            raise NoDevice("No weather station available")

        self.stations = {d["_id"]: d for d in self.raw_data}
        self.modules = {}
        for item in self.raw_data:
            if "modules" not in item:
                item["modules"] = [item]

            for module in item["modules"]:
                if "module_name" not in module:
                    if module["type"] == "NHC":
                        module["module_name"] = module["station_name"]
                    else:
                        continue
                self.modules[module["_id"]] = module
                self.modules[module["_id"]]["main_device"] = item["_id"]

        self.default_station = list(self.stations.values())[0]["station_name"]

    def modules_names_list(self, station_name=None, station_id=None):
        """Return a list of all modules for a given or all stations."""
        res = set()
        station_data = None
        if station_id is not None:
            station_data = self.station_by_id(station_id)
        elif station_name is not None:
            station_data = self.station_by_name(station_name)

        if station_data is not None:
            res.add(station_data.get("module_name", station_data.get("type")))
            for module in station_data["modules"]:
                res.add(module.get("module_name", module.get("type")))
        else:
            res.update([m["module_name"] for m in self.modules.values()])
            for station in self.stations.values():
                res.add(station.get("module_name", station.get("type")))
        return list(res)

    def get_modules(self, station_name=None, station_id=None):
        """Return a dict or modules for a given or all stations."""
        res = {}
        station_data = None
        if station_id is not None:
            station_data = self.station_by_id(station_id)
        elif station_name is not None:
            station_data = self.station_by_name(station_name)

        if station_data is not None:
            stations = [self.stations[station_data["_id"]]]
        else:
            stations = self.stations.values()
        for station in stations:
            res[station["_id"]] = {
                "station_name": station["station_name"],
                "module_name": station.get("module_name", station.get("type")),
                "id": station["_id"],
            }

            for module in station.get("modules", {}):
                res[module["_id"]] = {
                    "station_name": module.get("station_name", station["station_name"]),
                    "module_name": module.get("module_name", module.get("type")),
                    "id": module["_id"],
                }
        return res

    def station_by_name(self, station_name=None):
        """Return station by name."""
        if not station_name:
            station_name = self.default_station

        for station_data in self.stations.values():
            if station_data["station_name"] == station_name:
                return station_data
        return None

    def station_by_id(self, sid):
        """Return station by id."""
        return None if sid not in self.stations else self.stations[sid]

    def module_by_name(self, module_name, station_name=None):
        """Return module by name."""
        station = None
        if station_name:
            station = self.station_by_name(station_name)
            if not station:
                return None
            if station["module_name"] == module_name:
                return station

        else:
            for station in self.stations.values():
                if "module_name" in station:
                    if station["module_name"] == module_name:
                        return station
                    break

        for module in self.modules.values():
            if module["module_name"] == module_name:
                if not station or module["main_device"] == station["_id"]:
                    return module
        return None

    def module_by_id(self, mid, sid=None):
        """Return module by id."""
        station_data = self.station_by_id(sid) if sid else None
        if mid in self.modules:
            if station_data is not None:
                for module in station_data.get("modules"):
                    if module["_id"] == mid:
                        return module
            else:
                return self.modules[mid]

    def monitored_conditions(self, module=None, module_id=None):
        """Return monitored conditions for given module(s)."""
        if module_id:
            mod = self.module_by_id(module_id)
            if not mod:
                mod = self.station_by_id(module_id)
        elif module:
            mod = self.module_by_name(module)
            if not mod:
                mod = self.station_by_name(module)
        else:
            return None
        conditions = []
        if not mod:
            return conditions
        for cond in mod.get("data_type", []):
            if cond == "Wind":
                # the Wind meter actually exposes the following conditions
                conditions.extend(
                    ["WindAngle", "WindStrength", "GustAngle", "GustStrength"]
                )
            elif cond == "Rain":
                conditions.extend(["Rain", "sum_rain_24", "sum_rain_1"])
            else:
                conditions.append(cond)
        if mod["type"] in ["NAMain", "NHC"]:
            # the main module has wifi_status
            conditions.append("wifi_status")
        else:
            # assume all other modules have rf_status, battery_vp, and battery_percent
            conditions.extend(["rf_status", "battery_vp", "battery_percent"])
        if mod["type"] in ["NAMain", "NAModule1", "NAModule4", "NHC"]:
            conditions.extend(["min_temp", "max_temp"])
        if mod["type"] in [
            "NAMain",
            "NAModule1",
            "NAModule2",
            "NAModule3",
            "NAModule4",
            "NHC",
        ]:
            conditions.append("reachable")
        return conditions

    def last_data(self, station=None, exclude=0, by_id=False):
        """Return data for a given station and time frame."""
        key = "_id" if by_id else "module_name"
        if station is not None:
            stations = [station]
        elif by_id:
            stations = [s["_id"] for s in self.stations.values()]
        else:
            stations = [s["station_name"] for s in self.stations.values()]

        # Breaking change from Netatmo : dashboard_data no longer available if station lost
        last_data = {}
        for _station in stations:
            station_data = (
                self.station_by_id(_station)
                if by_id
                else self.station_by_name(_station)
            )
            if not station_data or "dashboard_data" not in station_data:
                LOG.info("No dashboard data for station %s", _station)
                continue

            # Define oldest acceptable sensor measure event
            limit = (time.time() - exclude) if exclude else 0
            dashboard_data = station_data["dashboard_data"]
            if key in station_data and dashboard_data["time_utc"] > limit:
                last_data[station_data[key]] = dashboard_data.copy()
                last_data[station_data[key]]["When"] = last_data[station_data[key]].pop(
                    "time_utc"
                )
                last_data[station_data[key]]["wifi_status"] = station_data[
                    "wifi_status"
                ]
                last_data[station_data[key]]["reachable"] = station_data["reachable"]

            for module in station_data["modules"]:
                if "dashboard_data" not in module or key not in module:
                    continue
                dashboard_data = module["dashboard_data"]
                if "time_utc" in dashboard_data and dashboard_data["time_utc"] > limit:
                    last_data[module[key]] = dashboard_data.copy()
                    last_data[module[key]]["When"] = last_data[module[key]].pop(
                        "time_utc"
                    )

                    for i in (
                        "rf_status",
                        "battery_vp",
                        "battery_percent",
                        "reachable",
                        "wifi_status",
                    ):
                        if i in module:
                            last_data[module[key]][i] = module[i]
        return last_data

    def check_not_updated(self, station=None, delay=3600):
        """Check if a given station has not been updated."""
        res = self.last_data(station)
        ret = []
        for i, value_data in res.items():
            if time.time() - value_data["When"] > delay:
                ret.append(i)
        return ret if ret else None

    def check_updated(self, station=None, delay=3600):
        """Check if a given station has been updated."""
        res = self.last_data(station)
        ret = []
        for i, value_data in res.items():
            if time.time() - value_data["When"] < delay:
                ret.append(i)
        return ret if ret else None

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
        post_params = {"device_id": device_id}
        if module_id:
            post_params["module_id"] = module_id
        post_params["scale"] = scale
        post_params["type"] = mtype
        if date_begin:
            post_params["date_begin"] = date_begin
        if date_end:
            post_params["date_end"] = date_end
        if limit:
            post_params["limit"] = limit
        post_params["optimize"] = "true" if optimize else "false"
        post_params["real_time"] = "true" if real_time else "false"
        return self.auth_data.post_request(url=_GETMEASURE_REQ, params=post_params)

    def min_max_th(self, station=None, module=None, frame="last24"):
        if not station:
            station = self.default_station
        station_data = self.station_by_name(station)
        if not station_data:
            station_data = self.station_by_id(station)
            if not station_data:
                return None

        if frame == "last24":
            end = time.time()
            start = end - 24 * 3600  # 24 hours ago
        elif frame == "day":
            start, end = today_stamps()

        if module and module != station_data["module_name"]:
            module_data = self.module_by_name(module, station_data["station_name"])
            if not module_data:
                module_data = self.module_by_id(station_data["_id"], module)
                if not module_data:
                    return None
            # retrieve module's data
            resp = self.get_measure(
                device_id=station_data["_id"],
                module_id=module_data["_id"],
                scale="max",
                mtype="Temperature,Humidity",
                date_begin=start,
                date_end=end,
            )
        else:  # retrieve station's data
            resp = self.get_measure(
                device_id=station_data["_id"],
                scale="max",
                mtype="Temperature,Humidity",
                date_begin=start,
                date_end=end,
            )

        if resp:
            temperatures = [v[0] for v in resp["body"].values()]
            humidities = [v[1] for v in resp["body"].values()]
            return (
                min(temperatures),
                max(temperatures),
                min(humidities),
                max(humidities),
            )
        return None
