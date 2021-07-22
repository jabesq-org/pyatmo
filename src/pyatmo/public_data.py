"""Support for Netatmo public weather data."""
from __future__ import annotations

import dataclasses
from abc import ABC
from collections import defaultdict
from typing import Any

from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .exceptions import NoDevice
from .helpers import _BASE_URL

_GETPUBLIC_DATA = _BASE_URL + "api/getpublicdata"

_STATION_TEMPERATURE_TYPE = "temperature"
_STATION_PRESSURE_TYPE = "pressure"
_STATION_HUMIDITY_TYPE = "humidity"

_ACCESSORY_RAIN_LIVE_TYPE = "rain_live"
_ACCESSORY_RAIN_60MIN_TYPE = "rain_60min"
_ACCESSORY_RAIN_24H_TYPE = "rain_24h"
_ACCESSORY_RAIN_TIME_TYPE = "rain_timeutc"
_ACCESSORY_WIND_STRENGTH_TYPE = "wind_strength"
_ACCESSORY_WIND_ANGLE_TYPE = "wind_angle"
_ACCESSORY_WIND_TIME_TYPE = "wind_timeutc"
_ACCESSORY_GUST_STRENGTH_TYPE = "gust_strength"
_ACCESSORY_GUST_ANGLE_TYPE = "gust_angle"


@dataclasses.dataclass
class Location:
    """Class of Netatmo public weather location."""

    lat_ne: str
    lon_ne: str
    lat_sw: str
    lon_sw: str


class AbstractPublicData(ABC):
    """Class of Netatmo public weather data."""

    raw_data: dict = defaultdict(dict)
    status: str = ""

    def process(self, resp: dict) -> None:
        """Process data from API."""
        self.status = resp.get("status", "")

    def stations_in_area(self) -> int:
        return len(self.raw_data)

    def get_latest_rain(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_RAIN_LIVE_TYPE)

    def get_average_rain(self) -> float:
        return average(self.get_latest_rain())

    def get_60_min_rain(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_RAIN_60MIN_TYPE)

    def get_average_60_min_rain(self) -> float:
        return average(self.get_60_min_rain())

    def get_24_h_rain(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_RAIN_24H_TYPE)

    def get_average_24_h_rain(self) -> float:
        return average(self.get_24_h_rain())

    def get_latest_pressures(self) -> dict:
        return self.get_latest_station_measures(_STATION_PRESSURE_TYPE)

    def get_average_pressure(self) -> float:
        return average(self.get_latest_pressures())

    def get_latest_temperatures(self) -> dict:
        return self.get_latest_station_measures(_STATION_TEMPERATURE_TYPE)

    def get_average_temperature(self) -> float:
        return average(self.get_latest_temperatures())

    def get_latest_humidities(self) -> dict:
        return self.get_latest_station_measures(_STATION_HUMIDITY_TYPE)

    def get_average_humidity(self) -> float:
        return average(self.get_latest_humidities())

    def get_latest_wind_strengths(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_WIND_STRENGTH_TYPE)

    def get_average_wind_strength(self) -> float:
        return average(self.get_latest_wind_strengths())

    def get_latest_wind_angles(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_WIND_ANGLE_TYPE)

    def get_latest_gust_strengths(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_GUST_STRENGTH_TYPE)

    def get_average_gust_strength(self) -> float:
        return average(self.get_latest_gust_strengths())

    def get_latest_gust_angles(self):
        return self.get_accessory_data(_ACCESSORY_GUST_ANGLE_TYPE)

    def get_locations(self) -> dict:
        return {
            station["_id"]: station["place"]["location"] for station in self.raw_data
        }

    def get_time_for_rain_measures(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_RAIN_TIME_TYPE)

    def get_time_for_wind_measures(self) -> dict:
        return self.get_accessory_data(_ACCESSORY_WIND_TIME_TYPE)

    def get_latest_station_measures(self, data_type) -> dict:
        measures: dict = {}
        for station in self.raw_data:
            for module in station["measures"].values():
                if (
                    "type" in module
                    and data_type in module["type"]
                    and "res" in module
                    and module["res"]
                ):
                    measure_index = module["type"].index(data_type)
                    latest_timestamp = sorted(module["res"], reverse=True)[0]
                    measures[station["_id"]] = module["res"][latest_timestamp][
                        measure_index
                    ]

        return measures

    def get_accessory_data(self, data_type: str) -> dict[str, Any]:
        data: dict = {}
        for station in self.raw_data:
            for module in station["measures"].values():
                if data_type in module:
                    data[station["_id"]] = module[data_type]

        return data


class PublicData(AbstractPublicData):
    """Class of Netatmo public weather data."""

    def __init__(
        self,
        auth: NetatmoOAuth2,
        lat_ne: str,
        lon_ne: str,
        lat_sw: str,
        lon_sw: str,
        required_data_type: str = None,
        filtering: bool = False,
    ) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
            LAT_NE {str} -- Latitude of the north east corner of the requested area. (-85 <= LAT_NE <= 85 and LAT_NE > LAT_SW)
            LON_NE {str} -- Longitude of the north east corner of the requested area. (-180 <= LON_NE <= 180 and LON_NE > LON_SW)
            LAT_SW {str} -- latitude of the south west corner of the requested area. (-85 <= LAT_SW <= 85)
            LON_SW {str} -- Longitude of the south west corner of the requested area. (-180 <= LON_SW <= 180)

        Keyword Arguments:
            required_data_type {str} -- comma-separated list from above _STATION or _ACCESSORY values (default: {None})
        """
        self.auth = auth
        self.required_data_type = required_data_type
        self.location = Location(lat_ne, lon_ne, lat_sw, lon_sw)
        self.filtering: bool = filtering

    def update(self) -> None:
        """Fetch and process data from API."""
        post_params: dict = {
            **dataclasses.asdict(self.location),
            "filter": self.filtering,
        }

        if self.required_data_type:
            post_params["required_data"] = self.required_data_type

        resp = self.auth.post_request(url=_GETPUBLIC_DATA, params=post_params).json()
        try:
            self.raw_data = resp["body"]
        except (KeyError, TypeError) as exc:
            raise NoDevice("No public weather data returned by Netatmo server") from exc

        self.process(resp)


class AsyncPublicData(AbstractPublicData):
    """Class of Netatmo public weather data."""

    def __init__(
        self,
        auth: AbstractAsyncAuth,
        lat_ne: str,
        lon_ne: str,
        lat_sw: str,
        lon_sw: str,
        required_data_type: str = None,
        filtering: bool = False,
    ) -> None:
        """Initialize self.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
            LAT_NE {str} -- Latitude of the north east corner of the requested area. (-85 <= LAT_NE <= 85 and LAT_NE > LAT_SW)
            LON_NE {str} -- Longitude of the north east corner of the requested area. (-180 <= LON_NE <= 180 and LON_NE > LON_SW)
            LAT_SW {str} -- latitude of the south west corner of the requested area. (-85 <= LAT_SW <= 85)
            LON_SW {str} -- Longitude of the south west corner of the requested area. (-180 <= LON_SW <= 180)

        Keyword Arguments:
            required_data_type {str} -- comma-separated list from above _STATION or _ACCESSORY values (default: {None})
        """
        self.auth = auth
        self.required_data_type = required_data_type
        self.location = Location(lat_ne, lon_ne, lat_sw, lon_sw)
        self.filtering: bool = filtering

    async def async_update(self) -> None:
        """Fetch and process data from API."""
        post_params: dict = {
            **dataclasses.asdict(self.location),
            "filter": self.filtering,
        }

        if self.required_data_type:
            post_params["required_data"] = self.required_data_type

        resp = await self.auth.async_post_request(
            url=_GETPUBLIC_DATA,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        resp_data = await resp.json()
        try:
            self.raw_data = resp_data["body"]
        except (KeyError, TypeError) as exc:
            raise NoDevice("No public weather data returned by Netatmo server") from exc

        self.process(resp_data)


def average(data: dict) -> float:
    return sum(data.values()) / len(data) if data else 0.0
