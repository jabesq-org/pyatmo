"""Support for a Netatmo account."""
from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING

from pyatmo.const import (
    _GETHOMECOACHDATA_REQ,
    _GETHOMESDATA_REQ,
    _GETHOMESTATUS_REQ,
    _GETSTATIONDATA_REQ,
    _SETSTATE_REQ,
)
from pyatmo.helpers import extract_raw_data_new
from pyatmo.home import NetatmoHome

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


class AbstractAccount(ABC):
    """Abstract class of a Netatmo account."""

    auth: AbstractAsyncAuth
    user: str | None
    homes: dict[str, NetatmoHome]
    raw_data: dict

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(user={self.user}, home_ids={self.homes.keys()}"
        )

    def process_topology(self) -> None:
        """Process topology information from /homesdata."""
        for home in self.raw_data["homes"]:
            if (home_id := home["id"]) in self.homes:
                self.homes[home_id].update_topology(home)
            else:
                self.homes[home_id] = NetatmoHome(self.auth, raw_data=home)


class AsyncAccount(AbstractAccount):
    """Async class of a Netatmo account."""

    def __init__(self, auth: AbstractAsyncAuth, favorite_stations: bool = True) -> None:
        """Initialize the Netatmo account.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth
        self.homes = {}
        self.favorite_stations = favorite_stations

    async def async_update_topology(self) -> None:
        """Retrieve topology data from /homesdata."""
        resp = await self.auth.async_post_request(url=_GETHOMESDATA_REQ)
        self.raw_data = extract_raw_data_new(await resp.json(), "homes")

        self.user = self.raw_data.get("user", {}).get("email")

        self.process_topology()

    async def async_update_status(self, home_id: str) -> None:
        """Retrieve status data from /homestatus."""
        resp = await self.auth.async_post_request(
            url=_GETHOMESTATUS_REQ,
            params={"home_id": home_id},
        )
        raw_data = extract_raw_data_new(await resp.json(), "home")
        self.homes[home_id].update(raw_data)

    async def async_update_weather_stations(self) -> None:
        """Retrieve status data from /getstationsdata."""
        params = {"get_favorites": ("true" if self.favorite_stations else "false")}
        await self._async_update_data(_GETSTATIONDATA_REQ, params=params)

    async def async_update_air_care(self) -> None:
        """Retrieve status data from /gethomecoachsdata."""
        await self._async_update_data(_GETHOMECOACHDATA_REQ)

    async def _async_update_data(self, endpoint: str, params: dict = None) -> None:
        """Retrieve status data from <endpoint>."""
        resp = await self.auth.async_post_request(url=endpoint, params=params)
        raw_data = extract_raw_data_new(await resp.json(), "devices")
        self.update_devices(raw_data)

    async def async_set_state(self, home_id: str, data: dict) -> None:
        """Modify device state by passing JSON specific to the device."""
        LOG.debug("Setting state: %s", data)

        post_params = {
            "json": {
                "home": {
                    "id": home_id,
                    **data,
                },
            },
        }
        resp = await self.auth.async_post_request(url=_SETSTATE_REQ, params=post_params)
        LOG.debug("Response: %s", resp)

    def update_devices(self, raw_data) -> None:
        """Update device states."""
        for device_data in raw_data["devices"]:
            if home_id := device_data.get(
                "home_id",
                self.find_home_of_device(device_data),
            ):
                if home_id not in self.homes:
                    continue
                self.homes[home_id].update(
                    {"home": {"modules": [fix_weather_attributes(device_data)]}},
                )
            for module_data in device_data.get("modules", []):
                self.update_devices({"devices": [module_data]})

    def find_home_of_device(self, device_data) -> str | None:
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


def fix_weather_attributes(raw_data) -> dict:
    result: dict = {}
    for attribute, value in raw_data.items():
        if attribute == "dashboard_data":
            result.update(**fix_weather_attributes(value))
        else:
            result[ATTRIBUTES_TO_FIX.get(attribute, attribute)] = value
    return result
