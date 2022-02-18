"""Module to represent Netatmo modules."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pyatmo.const import (
    ACCESSORY_GUST_ANGLE_TYPE,
    ACCESSORY_GUST_STRENGTH_TYPE,
    ACCESSORY_RAIN_24H_TYPE,
    ACCESSORY_RAIN_60MIN_TYPE,
    ACCESSORY_RAIN_LIVE_TYPE,
    ACCESSORY_WIND_ANGLE_TYPE,
    ACCESSORY_WIND_STRENGTH_TYPE,
    STATION_HUMIDITY_TYPE,
    STATION_PRESSURE_TYPE,
    STATION_TEMPERATURE_TYPE,
)
from pyatmo.modules.module import (
    BatteryMixin,
    BoilerMixin,
    CameraMixin,
    CO2Mixin,
    FirmwareMixin,
    FloodlightMixin,
    HumidityMixin,
    MonitoringMixin,
    NetatmoModule,
    NoiseMixin,
    PressureMixin,
    RainMixin,
    RfMixin,
    StatusMixin,
    TemperatureMixin,
    WifiMixin,
    WindMixin,
)

LOG = logging.getLogger(__name__)

# pylint: disable=R0901


class NRV(FirmwareMixin, RfMixin, BatteryMixin, NetatmoModule):
    ...


class NATherm1(FirmwareMixin, RfMixin, BatteryMixin, BoilerMixin, NetatmoModule):
    ...


class NAPlug(FirmwareMixin, RfMixin, WifiMixin, NetatmoModule):
    ...


class OTH(FirmwareMixin, WifiMixin, NetatmoModule):
    ...


class OTM(FirmwareMixin, RfMixin, BatteryMixin, BoilerMixin, NetatmoModule):
    ...


class NetatmoCamera(
    FirmwareMixin,
    MonitoringMixin,
    CameraMixin,
    WifiMixin,
    NetatmoModule,
):
    ...


class NACamera(NetatmoCamera):
    ...


class NOC(FloodlightMixin, NetatmoCamera):
    ...


class NDB(NetatmoCamera):
    ...


class NAMain(
    TemperatureMixin,
    HumidityMixin,
    CO2Mixin,
    NoiseMixin,
    PressureMixin,
    WifiMixin,
    FirmwareMixin,
    NetatmoModule,
):
    ...


class NAModule1(TemperatureMixin, HumidityMixin, RfMixin, FirmwareMixin, NetatmoModule):
    ...


class NAModule2(WindMixin, RfMixin, FirmwareMixin, NetatmoModule):
    ...


class NAModule3(RainMixin, RfMixin, FirmwareMixin, NetatmoModule):
    ...


class NAModule4(TemperatureMixin, RfMixin, FirmwareMixin, NetatmoModule):
    ...


class NHC(
    TemperatureMixin,
    HumidityMixin,
    CO2Mixin,
    PressureMixin,
    NoiseMixin,
    WifiMixin,
    FirmwareMixin,
    NetatmoModule,
):
    ...


class NACamDoorTag(StatusMixin, FirmwareMixin, BatteryMixin, RfMixin, NetatmoModule):
    ...


class NIS(
    StatusMixin,
    MonitoringMixin,
    FirmwareMixin,
    BatteryMixin,
    RfMixin,
    NetatmoModule,
):
    ...


@dataclass
class Location:
    """Class of Netatmo public weather location."""

    lat_ne: str
    lon_ne: str
    lat_sw: str
    lon_sw: str


@dataclass
class PublicWeatherArea:
    location: Location
    required_data_type: str | None
    filtering: bool
    modules: list[dict]

    def __init__(
        self,
        lat_ne: str,
        lon_ne: str,
        lat_sw: str,
        lon_sw: str,
        required_data_type: str | None = None,
        filtering: bool = False,
    ) -> None:
        self.location = Location(
            lat_ne,
            lon_ne,
            lat_sw,
            lon_sw,
        )
        self.modules = []
        self.required_data_type = required_data_type
        self.filtering = filtering

    def update(self, raw_data: dict) -> None:
        """Update public weather area with latest data."""
        self.modules = list(raw_data.get("public", []))

    def stations_in_area(self) -> int:
        """Return available number of stations in area."""
        return len(self.modules)

    def get_latest_rain(self) -> dict:
        return self.get_accessory_data(ACCESSORY_RAIN_LIVE_TYPE)

    def get_60_min_rain(self) -> dict:
        return self.get_accessory_data(ACCESSORY_RAIN_60MIN_TYPE)

    def get_24_h_rain(self) -> dict:
        return self.get_accessory_data(ACCESSORY_RAIN_24H_TYPE)

    def get_latest_pressures(self) -> dict:
        return self.get_latest_station_measures(STATION_PRESSURE_TYPE)

    def get_latest_temperatures(self) -> dict:
        return self.get_latest_station_measures(STATION_TEMPERATURE_TYPE)

    def get_latest_humidities(self) -> dict:
        return self.get_latest_station_measures(STATION_HUMIDITY_TYPE)

    def get_latest_wind_strengths(self) -> dict:
        return self.get_accessory_data(ACCESSORY_WIND_STRENGTH_TYPE)

    def get_latest_wind_angles(self) -> dict:
        return self.get_accessory_data(ACCESSORY_WIND_ANGLE_TYPE)

    def get_latest_gust_strengths(self) -> dict:
        return self.get_accessory_data(ACCESSORY_GUST_STRENGTH_TYPE)

    def get_latest_gust_angles(self):
        return self.get_accessory_data(ACCESSORY_GUST_ANGLE_TYPE)

    def get_latest_station_measures(self, data_type) -> dict:
        measures: dict = {}
        for station in self.modules:
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
        for station in self.modules:
            for module in station["measures"].values():
                if data_type in module:
                    data[station["_id"]] = module[data_type]

        return data
