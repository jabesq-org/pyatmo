"""Support for a Netatmo account."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast
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
    RawData,
)
from pyatmo.helpers import extract_raw_data
from pyatmo.home import Home
from pyatmo.modules.module import Energy, MeasureInterval, Module

if TYPE_CHECKING:
    from aiohttp import ClientResponse

    from pyatmo.auth import AbstractAsyncAuth

LOG: logging.Logger = logging.getLogger(__name__)


class AsyncAccount:
    """Async class of a Netatmo account."""

    def __init__(
        self,
        auth: AbstractAsyncAuth,
        favorite_stations: bool = True,
    ) -> None:
        """Initialize the Netatmo account."""

        self.auth: AbstractAsyncAuth = auth
        self.user: str | None = None
        self.all_homes_id: dict[str, str] = {}
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

    def process_topology(self, disabled_homes_ids: list[str] | None = None) -> None:
        """Process topology information from /homesdata."""

        if disabled_homes_ids is None:
            disabled_homes_ids = []

        for home in self.raw_data["homes"]:
            home_id: str = home.get("id", "Unknown")
            home_name: str = home.get("name", "Unknown")
            self.all_homes_id[home_id] = home_name

            if home_id in disabled_homes_ids:
                if home_id in self.homes:
                    del self.homes[home_id]
                continue

            if home_id in self.homes:
                self.homes[home_id].update_topology(home)
            else:
                self.homes[home_id] = Home(self.auth, raw_data=home)

    async def async_update_topology(
        self,
        disabled_homes_ids: list[str] | None = None,
    ) -> None:
        """Retrieve topology data from /homesdata."""

        resp = await self.auth.async_post_api_request(
            endpoint=GETHOMESDATA_ENDPOINT,
        )
        self.raw_data = extract_raw_data(await resp.json(), "homes")

        self.user = self.raw_data.get("user", {}).get("email")

        self.process_topology(disabled_homes_ids=disabled_homes_ids)

    async def async_update_status(self, home_id: str) -> None:
        """Retrieve status data from /homestatus."""
        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=GETHOMESTATUS_ENDPOINT,
            params={"home_id": home_id},
        )
        raw_data: RawData = extract_raw_data(await resp.json(), HOME)
        await self.homes[home_id].update(raw_data, do_raise_for_reachability_error=True)

    async def async_update_events(self, home_id: str) -> None:
        """Retrieve events from /getevents."""
        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=GETEVENTS_ENDPOINT,
            params={"home_id": home_id},
        )
        raw_data: RawData = extract_raw_data(await resp.json(), HOME)
        await self.homes[home_id].update(raw_data)

    async def async_update_weather_stations(self) -> None:
        """Retrieve status data from /getstationsdata."""
        params: dict[str, str] = {
            "get_favorites": ("true" if self.favorite_stations else "false")
        }
        await self._async_update_data(
            GETSTATIONDATA_ENDPOINT,
            params=params,
        )

    async def async_update_air_care(self) -> None:
        """Retrieve status data from /gethomecoachsdata."""
        await self._async_update_data(GETHOMECOACHDATA_ENDPOINT)

    async def async_update_measures(
        self,
        home_id: str,
        module_id: str,
        start_time: int | None = None,
        end_time: int | None = None,
        interval: MeasureInterval = MeasureInterval.HOUR,
        days: int = 7,
    ) -> None:
        """Retrieve measures data from /getmeasure."""

        module: Module = self.homes[home_id].modules[module_id]
        if module.has_feature("historical_data"):
            module = cast("Energy", module)
            await module.async_update_measures(
                start_time=start_time,
                end_time=end_time,
                interval=interval,
                days=days,
            )

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

    async def async_update_public_weather(self, area_id: str) -> None:
        """Retrieve status data from /getpublicdata."""
        params: dict[str, str] = {
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

    async def _async_update_data(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        tag: str = "devices",
        area_id: str | None = None,
    ) -> None:
        """Retrieve status data from <endpoint>."""
        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=endpoint, params=params
        )
        raw_data: RawData = extract_raw_data(await resp.json(), tag)
        await self.update_devices(raw_data, area_id)

    async def async_set_state(self, home_id: str, data: dict[str, Any]) -> None:
        """Modify device state by passing JSON specific to the device."""
        LOG.debug("Setting state: %s", data)

        post_params: dict[str, Any] = {
            "json": {
                HOME: {
                    "id": home_id,
                    **data,
                },
            },
        }
        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=SETSTATE_ENDPOINT,
            params=post_params,
        )
        LOG.debug("Response: %s", resp)

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
                    modules_data: list[dict[str, Any]] = []
                    for module_data in device_data.get("modules", []):
                        module_data["home_id"] = home_id
                        module_data["id"] = module_data["_id"]
                        module_data["name"] = module_data.get("module_name")
                        modules_data.append(normalize_weather_attributes(module_data))
                    modules_data.append(normalize_weather_attributes(device_data))

                    self.homes[home_id] = Home(
                        self.auth,
                        raw_data={
                            "id": home_id,
                            "name": device_data.get("home_name", "Unknown"),
                            "modules": modules_data,
                        },
                    )
                await self.homes[home_id].update(
                    {HOME: {"modules": [normalize_weather_attributes(device_data)]}},
                )
            else:
                LOG.debug("No home %s (%s) found.", home_id, home_id)

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


ATTRIBUTES_TO_FIX: dict[str, str] = {
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
