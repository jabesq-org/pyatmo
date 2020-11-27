import logging
import time
from typing import Dict, List, Optional, Tuple

from .auth import NetatmoOAuth2
from .exceptions import NoDevice
from .helpers import _BASE_URL, fix_id, today_stamps

LOG = logging.getLogger(__name__)

_GETMEASURE_REQ = _BASE_URL + "api/getmeasure"
_GETSTATIONDATA_REQ = _BASE_URL + "api/getstationsdata"


class WeatherStationData:
    """Class of Netatmo Weather Station devices (stations and modules)."""

    def __init__(self, auth: NetatmoOAuth2, url_req: str = None) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token

        Raises:
            NoDevice: No devices found.
        """
        self.url_req = url_req or _GETSTATIONDATA_REQ
        self.auth = auth

        resp = self.auth.post_request(url=self.url_req)

        if resp is None or "body" not in resp:
            raise NoDevice("No weather station data returned by Netatmo server")

        try:
            self.raw_data = fix_id(resp["body"].get("devices"))
        except KeyError as exc:
            LOG.debug("No <body> in response %s", resp)
            raise NoDevice(
                "No weather station data returned by Netatmo server",
            ) from exc

        if not self.raw_data:
            raise NoDevice("No weather station available")

        self.stations = {d["_id"]: d for d in self.raw_data}
        self.modules = {}

        for item in self.raw_data:
            # The station name is sometimes not contained in the backend data
            if "station_name" not in item:
                item["station_name"] = item.get("home_name", item["type"])

            if "modules" not in item:
                item["modules"] = [item]

            for module in item["modules"]:
                if "module_name" not in module and module["type"] == "NHC":
                    module["module_name"] = module["station_name"]

                self.modules[module["_id"]] = module
                self.modules[module["_id"]]["main_device"] = item["_id"]

    def get_module_names(self, station_id: str) -> List:
        """Return a list of all module names for a given station."""
        res = set()
        station_data = self.get_station(station_id)

        if not station_data:
            return []

        res.add(station_data.get("module_name", station_data.get("type")))
        for module in station_data["modules"]:
            # Add module name, use module type if no name is available
            res.add(module.get("module_name", module.get("type")))

        return list(res)

    def get_modules(self, station_id: str) -> Dict:
        """Return a dict of modules per given station."""
        station_data = self.get_station(station_id)

        if not station_data:
            return {}

        res = {}
        for station in [self.stations[station_data["_id"]]]:
            station_type = station.get("type")
            station_name = station.get("station_name", station_type)
            res[station["_id"]] = {
                "station_name": station_name,
                "module_name": station.get("module_name", station_type),
                "id": station["_id"],
            }

            for module in station["modules"]:
                res[module["_id"]] = {
                    "station_name": module.get("station_name", station_name),
                    "module_name": module.get("module_name", module.get("type")),
                    "id": module["_id"],
                }

        return res

    def get_station(self, station_id: str) -> Dict:
        """Return station by id."""
        return self.stations.get(station_id, {})

    def get_module(self, module_id: str) -> Dict:
        """Return module by id."""
        return self.modules.get(module_id, {})

    def get_monitored_conditions(self, module_id: str) -> List:
        """Return monitored conditions for given module."""
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
                    ["WindAngle", "WindStrength", "GustAngle", "GustStrength"],
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

        if module["type"] in ["NAMain", "NAModule1", "NAModule4"]:
            conditions.extend(["temp_trend"])

        if module["type"] == "NAMain":
            conditions.extend(["pressure_trend"])

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

    def get_last_data(self, station_id: str, exclude: int = 0) -> Dict:
        """Return data for a given station and time frame."""
        key = "_id"

        # Breaking change from Netatmo : dashboard_data no longer available if station lost
        last_data: Dict = {}
        station = self.get_station(station_id)

        if not station or "dashboard_data" not in station:
            LOG.debug("No dashboard data for station %s", station_id)
            return last_data

        # Define oldest acceptable sensor measure event
        limit = (time.time() - exclude) if exclude else 0

        data = station["dashboard_data"]
        if key in station and data["time_utc"] > limit:
            last_data[station[key]] = data.copy()
            last_data[station[key]]["When"] = last_data[station[key]].pop("time_utc")
            last_data[station[key]]["wifi_status"] = station.get("wifi_status")
            last_data[station[key]]["reachable"] = station.get("reachable")

        for module in station["modules"]:

            if "dashboard_data" not in module or key not in module:
                continue

            data = module["dashboard_data"]
            if "time_utc" in data and data["time_utc"] > limit:
                last_data[module[key]] = data.copy()
                last_data[module[key]]["When"] = last_data[module[key]].pop("time_utc")

                # For potential use, add battery and radio coverage information to module data if present
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

    def check_not_updated(self, station_id: str, delay: int = 3600) -> List:
        """Check if a given station has not been updated."""
        res = self.get_last_data(station_id)
        return [
            key for key, value in res.items() if time.time() - value["When"] > delay
        ]

    def check_updated(self, station_id: str, delay: int = 3600) -> List:
        """Check if a given station has been updated."""
        res = self.get_last_data(station_id)
        return [
            key for key, value in res.items() if time.time() - value["When"] < delay
        ]

    def get_data(
        self,
        device_id: str,
        scale: str,
        module_type: str,
        module_id: str = None,
        date_begin: float = None,
        date_end: float = None,
        limit: int = None,
        optimize: bool = False,
        real_time: bool = False,
    ) -> Optional[Dict]:
        """Retrieve data from a device or module."""
        post_params = {"device_id": device_id}
        if module_id:
            post_params["module_id"] = module_id

        post_params["scale"] = scale
        post_params["type"] = module_type

        if date_begin:
            post_params["date_begin"] = f"{date_begin}"

        if date_end:
            post_params["date_end"] = f"{date_end}"

        if limit:
            post_params["limit"] = f"{limit}"

        post_params["optimize"] = "true" if optimize else "false"
        post_params["real_time"] = "true" if real_time else "false"

        return self.auth.post_request(url=_GETMEASURE_REQ, params=post_params)

    def get_min_max_t_h(
        self,
        station_id: str,
        module_id: str = None,
        frame: str = "last24",
    ) -> Optional[Tuple[float, float, float, float]]:
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
            start, end = today_stamps()

        else:
            raise ValueError("'frame' value can only be 'last24' or 'day'")

        resp = self.get_data(
            device_id=station_id,
            module_id=module_id,
            scale="max",
            module_type="Temperature,Humidity",
            date_begin=start,
            date_end=end,
        )

        if resp:
            temperature = [temp[0] for temp in resp["body"].values()]
            humidity = [hum[1] for hum in resp["body"].values()]
            return min(temperature), max(temperature), min(humidity), max(humidity)

        return None
