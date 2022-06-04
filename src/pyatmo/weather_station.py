"""Support for Netatmo weather station devices (stations and modules)."""
from __future__ import annotations

import logging
import time
from abc import ABC
from collections import defaultdict
from warnings import warn

from pyatmo.auth import AbstractAsyncAuth, NetatmoOAuth2
from pyatmo.const import GETMEASURE_ENDPOINT, GETSTATIONDATA_ENDPOINT
from pyatmo.helpers import extract_raw_data, today_stamps

LOG = logging.getLogger(__name__)


warn(f"The module {__name__} is deprecated.", DeprecationWarning, stacklevel=2)


class AbstractWeatherStationData(ABC):
    """Abstract class of Netatmo Weather Station devices."""

    raw_data: dict = defaultdict(dict)
    stations: dict = defaultdict(dict)
    modules: dict = defaultdict(dict)

    def process(self) -> None:
        """Process data from API."""
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

    def get_module_names(self, station_id: str) -> list:
        """Return a list of all module names for a given station."""
        if not (station_data := self.get_station(station_id)):
            return []

        res = {station_data.get("module_name", station_data.get("type"))}
        for module in station_data["modules"]:
            # Add module name, use module type if no name is available
            res.add(module.get("module_name", module.get("type")))

        return list(res)

    def get_modules(self, station_id: str) -> dict:
        """Return a dict of modules per given station."""
        if not (station_data := self.get_station(station_id)):
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

    def get_station(self, station_id: str) -> dict:
        """Return station by id."""
        return self.stations.get(station_id, {})

    def get_module(self, module_id: str) -> dict:
        """Return module by id."""
        return self.modules.get(module_id, {})

    def get_monitored_conditions(self, module_id: str) -> list:
        """Return monitored conditions for given module."""
        if not (module := (self.get_module(module_id) or self.get_station(module_id))):
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

    def get_last_data(self, station_id: str, exclude: int = 0) -> dict:
        """Return data for a given station and time frame."""
        key = "_id"

        last_data: dict = {}

        if (
            not (station := self.get_station(station_id))
            or "dashboard_data" not in station
        ):
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

                # For potential use, add battery and radio coverage information
                # to module data if present
                for val in (
                    "rf_status",
                    "battery_vp",
                    "battery_percent",
                    "reachable",
                    "wifi_status",
                ):
                    if val in module:
                        last_data[module[key]][val] = module[val]

        return last_data

    def check_not_updated(self, station_id: str, delay: int = 3600) -> list:
        """Check if a given station has not been updated."""
        res = self.get_last_data(station_id)
        return [
            key for key, value in res.items() if time.time() - value["When"] > delay
        ]

    def check_updated(self, station_id: str, delay: int = 3600) -> list:
        """Check if a given station has been updated."""
        res = self.get_last_data(station_id)
        return [
            key for key, value in res.items() if time.time() - value["When"] < delay
        ]


class WeatherStationData(AbstractWeatherStationData):
    """Class of Netatmo weather station devices."""

    def __init__(
        self,
        auth: NetatmoOAuth2,
        endpoint: str = GETSTATIONDATA_ENDPOINT,
        favorites: bool = True,
    ) -> None:
        """Initialize the Netatmo weather station data.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
            url_req {str} -- Optional request endpoint
        """
        self.auth = auth
        self.endpoint = endpoint
        self.params = {"get_favorites": ("true" if favorites else "false")}

    def update(self):
        """Fetch data from API."""
        self.raw_data = extract_raw_data(
            self.auth.post_api_request(
                endpoint=self.endpoint,
                params=self.params,
            ).json(),
            "devices",
        )
        self.process()

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
    ) -> dict | None:
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

        return self.auth.post_api_request(
            endpoint=GETMEASURE_ENDPOINT,
            params=post_params,
        ).json()

    def get_min_max_t_h(
        self,
        station_id: str,
        module_id: str = None,
        frame: str = "last24",
    ) -> tuple[float, float, float, float] | None:
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

        if resp := self.get_data(
            device_id=station_id,
            module_id=module_id,
            scale="max",
            module_type="Temperature,Humidity",
            date_begin=start,
            date_end=end,
        ):
            temperature = [temp[0] for temp in resp["body"].values()]
            humidity = [hum[1] for hum in resp["body"].values()]
            return min(temperature), max(temperature), min(humidity), max(humidity)

        return None


class AsyncWeatherStationData(AbstractWeatherStationData):
    """Class of Netatmo weather station devices."""

    def __init__(
        self,
        auth: AbstractAsyncAuth,
        endpoint: str = GETSTATIONDATA_ENDPOINT,
        favorites: bool = True,
    ) -> None:
        """Initialize the Netatmo weather station data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
            url_req {str} -- Optional request endpoint
        """
        self.auth = auth
        self.endpoint = endpoint
        self.params = {"get_favorites": ("true" if favorites else "false")}

    async def async_update(self):
        """Fetch data from API."""
        resp = await self.auth.async_post_api_request(
            endpoint=self.endpoint,
            params=self.params,
        )

        assert not isinstance(resp, bytes)
        self.raw_data = extract_raw_data(await resp.json(), "devices")
        self.process()
