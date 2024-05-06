"""Support for a Netatmo account."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pyatmo import modules
from pyatmo.const import (
    GETEVENTS_ENDPOINT,
    GETHOMECOACHDATA_ENDPOINT,
    GETHOMESDATA_ENDPOINT,
    GETHOMESTATUS_ENDPOINT,
    GETPUBLIC_DATA_ENDPOINT,
    GETSTATIONDATA_ENDPOINT,
    HOME,
    SETSTATE_ENDPOINT,
    MeasureInterval,
    RawData,
)
from pyatmo.exceptions import ApiHomeReachabilityError
from pyatmo.helpers import extract_raw_data
from pyatmo.home import Home
from pyatmo.modules.module import Module

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


class AsyncAccount:
    """Async class of a Netatmo account."""

    def __init__(
            self,
            auth: AbstractAsyncAuth,
            favorite_stations: bool = True,
            support_only_homes: list | None = None,
    ) -> None:
        """Initialize the Netatmo account."""

        self.auth: AbstractAsyncAuth = auth
        self.user: str | None = None
        self.support_only_homes = support_only_homes
        self.all_account_homes: dict[str, Home] = {}
        self.additional_public_homes: dict[str, Home] = {}
        self.homes: dict[str, Home] = {}
        self.raw_data: RawData = {}
        self.favorite_stations: bool = favorite_stations
        self.public_weather_areas: dict[str, modules.PublicWeatherArea] = {}
        self.modules: dict[str, Module] = {}


    def __repr__(self) -> str:
        """Return the representation."""

        return (
            f"{self.__class__.__name__}(user={self.user}, home_ids={self.homes.keys()}"
        )


    def update_supported_homes(self, support_only_homes: list | None = None):
        """Update the exposed/supported homes."""

        if support_only_homes is None or len(support_only_homes) == 0:
            self.homes = copy.copy(self.all_account_homes)
        else:
            self.homes = {}
            for h_id in support_only_homes:
                h = self.all_account_homes.get(h_id)
                if h is not None:
                    self.homes[h_id] = h

        if len(self.homes) == 0:
            self.homes = copy.copy(self.all_account_homes)

        self.support_only_homes = list(self.homes)

        self.homes.update(self.additional_public_homes)


    def process_topology(self) -> None:
        """Process topology information from /homesdata."""

        for home in self.raw_data["homes"]:
            if (home_id := home["id"]) in self.all_account_homes:
                self.all_account_homes[home_id].update_topology(home)
            else:
                self.all_account_homes[home_id] = Home(self.auth, raw_data=home)

        self.update_supported_homes(self.support_only_homes)


    async def async_update_topology(self) -> int:
        """Retrieve topology data from /homesdata. Returns the number of performed API calls."""

        resp = await self.auth.async_post_api_request(
            endpoint=GETHOMESDATA_ENDPOINT,
        )
        self.raw_data = extract_raw_data(await resp.json(), "homes")

        self.user = self.raw_data.get("user", {}).get("email")

        self.process_topology()

        return 1


    async def async_update_status(self, home_id: str | None = None) -> int:
        """Retrieve status data from /homestatus. Returns the number of performed API calls."""

        if home_id is None:
            self.update_supported_homes(self.support_only_homes)
            homes = self.homes
        else:
            homes = [home_id]
        num_calls = 0
        all_homes_ok = True
        for h_id in homes:
            resp = await self.auth.async_post_api_request(
                endpoint=GETHOMESTATUS_ENDPOINT,
                params={"home_id": h_id},
            )
            raw_data = extract_raw_data(await resp.json(), HOME)
            is_correct_update = await self.homes[h_id].update(raw_data)
            if not is_correct_update:
                all_homes_ok = False
            num_calls += 1

        if all_homes_ok is False:
            raise ApiHomeReachabilityError(
                "No Home update could be performed, all modules unreachable and not updated",
            )

        return num_calls


    async def async_update_events(self, home_id: str) -> int:
        """Retrieve events from /getevents. Returns the number of performed API calls."""
        resp = await self.auth.async_post_api_request(
            endpoint=GETEVENTS_ENDPOINT,
            params={"home_id": home_id},
        )
        raw_data = extract_raw_data(await resp.json(), HOME)
        await self.homes[home_id].update(raw_data)

        return 1


    async def async_update_weather_stations(self) -> int:
        """Retrieve status data from /getstationsdata. Returns the number of performed API calls."""
        params = {"get_favorites": ("true" if self.favorite_stations else "false")}
        await self._async_update_data(
            GETSTATIONDATA_ENDPOINT,
            params=params,
        )
        return 1


    async def async_update_air_care(self) -> int:
        """Retrieve status data from /gethomecoachsdata. Returns the number of performed API calls."""
        await self._async_update_data(GETHOMECOACHDATA_ENDPOINT)

        return 1


    async def async_update_measures(
            self,
            home_id: str,
            module_id: str,
            start_time: int | None = None,
            interval: MeasureInterval = MeasureInterval.HOUR,
            days: int = 7,
            end_time: int | None = None,
    ) -> int:
        """Retrieve measures data from /getmeasure. Returns the number of performed API calls."""

        num_calls = await getattr(
            self.homes[home_id].modules[module_id], "async_update_measures"
        )(
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            days=days,
        )
        return num_calls


    def register_public_weather_area(
            self,
            lat_ne: str,
            lon_ne: str,
            lat_sw: str,
            lon_sw: str,
            required_data_type: str | None = None,
            filtering: bool = False,
            *,
            area_id: str = str(uuid4()),
    ) -> str:
        """Register public weather area to monitor."""

        self.public_weather_areas[area_id] = modules.PublicWeatherArea(
            lat_ne,
            lon_ne,
            lat_sw,
            lon_sw,
            required_data_type,
            filtering,
        )
        return area_id


    async def async_update_public_weather(self, area_id: str) -> int:
        """Retrieve status data from /getpublicdata. Returns the number of performed API calls."""
        params = {
            "lat_ne": self.public_weather_areas[area_id].location.lat_ne,
            "lon_ne": self.public_weather_areas[area_id].location.lon_ne,
            "lat_sw": self.public_weather_areas[area_id].location.lat_sw,
            "lon_sw": self.public_weather_areas[area_id].location.lon_sw,
            "filtering": (
                "true" if self.public_weather_areas[area_id].filtering else "false"
            ),
        }
        await self._async_update_data(
            GETPUBLIC_DATA_ENDPOINT,
            tag="body",
            params=params,
            area_id=area_id,
        )

        return 1


    async def _async_update_data(
            self,
            endpoint: str,
            params: dict[str, Any] | None = None,
            tag: str = "devices",
            area_id: str | None = None,
    ) -> None:
        """Retrieve status data from <endpoint>."""
        resp = await self.auth.async_post_api_request(endpoint=endpoint, params=params)
        raw_data = extract_raw_data(await resp.json(), tag)
        await self.update_devices(raw_data, area_id)


    async def async_set_state(self, home_id: str, data: dict[str, Any]) -> int:
        """Modify device state by passing JSON specific to the device. Returns the number of performed API calls."""
        LOG.debug("Setting state: %s", data)

        post_params = {
            "json": {
                HOME: {
                    "id": home_id,
                    **data,
                },
            },
        }
        resp = await self.auth.async_post_api_request(
            endpoint=SETSTATE_ENDPOINT,
            params=post_params,
        )
        LOG.debug("Response: %s", resp)
        return 1


    async def update_devices(
            self,
            raw_data: RawData,
            area_id: str | None = None,
    ) -> None:
        """Update device states."""
        for device_data in raw_data.get("devices", {}):
            if home_id := device_data.get(
                    "home_id",
                    self.find_home_of_device(device_data),
            ):
                if home_id not in self.homes:
                    modules_data = []
                    for module_data in device_data.get("modules", []):
                        module_data["home_id"] = home_id
                        module_data["id"] = module_data["_id"]
                        module_data["name"] = module_data.get("module_name")
                        modules_data.append(normalize_weather_attributes(module_data))
                    modules_data.append(normalize_weather_attributes(device_data))

                    self.additional_public_homes[home_id] = Home(
                        self.auth,
                        raw_data={
                            "id": home_id,
                            "name": device_data.get("home_name", "Unknown"),
                            "modules": modules_data,
                        },
                    )
                    self.update_supported_homes(self.support_only_homes)

                await self.homes[home_id].update(
                    {HOME: {"modules": [normalize_weather_attributes(device_data)]}},
                )
            else:
                LOG.debug("No home %s found.", home_id)

            for module_data in device_data.get("modules", []):
                module_data["home_id"] = home_id
                await self.update_devices({"devices": [module_data]})

            if (
                    device_data["type"] == "NHC"
                    or self.find_home_of_device(device_data) is None
            ):
                device_data["name"] = device_data.get(
                    "station_name",
                    device_data.get("module_name", "Unknown"),
                )
                device_data = normalize_weather_attributes(device_data)
                if device_data["id"] not in self.modules:
                    self.modules[device_data["id"]] = getattr(
                        modules,
                        device_data["type"],
                    )(
                        home=self,
                        module=device_data,
                    )
                await self.modules[device_data["id"]].update(device_data)

                if device_data.get("modules", []):
                    self.modules[device_data["id"]].modules = [
                        module["_id"] for module in device_data["modules"]
                    ]

        if area_id is not None:
            self.public_weather_areas[area_id].update(raw_data)


    def find_home_of_device(self, device_data: dict[str, Any]) -> str | None:
        """Find home_id of device."""
        return next(
            (
                home_id
                for home_id, home in self.homes.items()
                if device_data["_id"] in home.modules
            ),
            None,
        )


ATTRIBUTES_TO_FIX = {
    "_id": "id",
    "firmware": "firmware_revision",
    "wifi_status": "wifi_strength",
    "rf_status": "rf_strength",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Pressure": "pressure",
    "CO2": "co2",
    "AbsolutePressure": "absolute_pressure",
    "Noise": "noise",
    "Rain": "rain",
    "WindStrength": "wind_strength",
    "WindAngle": "wind_angle",
    "GustStrength": "gust_strength",
    "GustAngle": "gust_angle",
}


def normalize_weather_attributes(raw_data: RawData) -> dict[str, Any]:
    """Normalize weather attributes."""
    result: dict[str, Any] = {}
    for attribute, value in raw_data.items():
        if attribute == "dashboard_data":
            result.update(**normalize_weather_attributes(value))
        else:
            result[ATTRIBUTES_TO_FIX.get(attribute, attribute)] = value
    return result
