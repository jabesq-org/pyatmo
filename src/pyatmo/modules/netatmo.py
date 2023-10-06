"""Module to represent Netatmo modules."""
from __future__ import annotations

from dataclasses import dataclass
import logging
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
    RawData,
)
from pyatmo.modules.module import (
    BatteryMixin,
    BoilerMixin,
    Camera,
    CO2Mixin,
    FirmwareMixin,
    FloodlightMixin,
    HealthIndexMixin,
    HumidityMixin,
    Module,
    MonitoringMixin,
    NoiseMixin,
    PlaceMixin,
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


class NRV(FirmwareMixin, RfMixin, BatteryMixin, Module):
    """Class to represent a Netatmo NRV."""

    ...


class NATherm1(FirmwareMixin, RfMixin, BatteryMixin, BoilerMixin, Module):
    """Class to represent a Netatmo NATherm1."""

    ...


class NAPlug(FirmwareMixin, RfMixin, WifiMixin, Module):
    """Class to represent a Netatmo NAPlug."""

    ...


class OTH(FirmwareMixin, WifiMixin, Module):
    """Class to represent a Netatmo OTH."""

    ...


class OTM(FirmwareMixin, RfMixin, BatteryMixin, BoilerMixin, Module):
    """Class to represent a Netatmo OTM."""

    ...


class NACamera(Camera):
    """Class to represent a Netatmo NACamera."""

    ...


class NOC(FloodlightMixin, Camera):
    """Class to represent a Netatmo NOC."""

    ...


class NDB(Camera):
    """Class to represent a Netatmo NDB."""

    ...


class NAMain(
    TemperatureMixin,
    HumidityMixin,
    CO2Mixin,
    NoiseMixin,
    PressureMixin,
    WifiMixin,
    FirmwareMixin,
    PlaceMixin,
    Module,
):
    """Class to represent a Netatmo NAMain."""

    ...


class NAModule1(
    TemperatureMixin,
    HumidityMixin,
    RfMixin,
    FirmwareMixin,
    BatteryMixin,
    PlaceMixin,
    Module,
):
    """Class to represent a Netatmo NAModule1."""

    ...


class NAModule2(WindMixin, RfMixin, FirmwareMixin, BatteryMixin, PlaceMixin, Module):
    """Class to represent a Netatmo NAModule2."""

    ...


class NAModule3(RainMixin, RfMixin, FirmwareMixin, BatteryMixin, PlaceMixin, Module):
    """Class to represent a Netatmo NAModule3."""

    ...


class NAModule4(
    TemperatureMixin,
    CO2Mixin,
    HumidityMixin,
    RfMixin,
    FirmwareMixin,
    BatteryMixin,
    PlaceMixin,
    Module,
):
    """Class to represent a Netatmo NAModule4."""

    ...


class NHC(
    TemperatureMixin,
    HumidityMixin,
    CO2Mixin,
    PressureMixin,
    NoiseMixin,
    HealthIndexMixin,
    WifiMixin,
    FirmwareMixin,
    PlaceMixin,
    Module,
):
    """Class to represent a Netatmo NHC."""

    ...


class NACamDoorTag(StatusMixin, FirmwareMixin, BatteryMixin, RfMixin, Module):
    """Class to represent a Netatmo NACamDoorTag."""

    ...


class NIS(
    StatusMixin,
    MonitoringMixin,
    FirmwareMixin,
    BatteryMixin,
    RfMixin,
    Module,
):
    """Class to represent a Netatmo NIS."""

    ...


class NSD(
    FirmwareMixin,
    Module,
):
    """Class to represent a Netatmo NSD."""

    ...


class NCO(
    FirmwareMixin,
    Module,
):
    """Class to represent a Netatmo NCO."""

    ...


@dataclass
class Location:
    """Class of Netatmo public weather location."""

    lat_ne: str
    lon_ne: str
    lat_sw: str
    lon_sw: str


class PublicWeatherArea:
    """Class of Netatmo public weather data."""

    location: Location
    required_data_type: str | None
    filtering: bool
    modules: list[dict[str, Any]]

    def __init__(
        self,
        lat_ne: str,
        lon_ne: str,
        lat_sw: str,
        lon_sw: str,
        required_data_type: str | None = None,
        filtering: bool = False,
    ) -> None:
        """Initialize self."""

        self.location = Location(
            lat_ne,
            lon_ne,
            lat_sw,
            lon_sw,
        )
        self.modules = []
        self.required_data_type = required_data_type
        self.filtering = filtering

    def update(self, raw_data: RawData) -> None:
        """Update public weather area with the latest data."""

        self.modules = list(raw_data.get("public", []))

    def stations_in_area(self) -> int:
        """Return available number of stations in area."""

        return len(self.modules)

    def get_latest_rain(self) -> dict[str, Any]:
        """Return latest rain measures."""
        return self.get_accessory_data(ACCESSORY_RAIN_LIVE_TYPE)

    def get_60_min_rain(self) -> dict[str, Any]:
        """Return 60 min rain measures."""
        return self.get_accessory_data(ACCESSORY_RAIN_60MIN_TYPE)

    def get_24_h_rain(self) -> dict[str, Any]:
        """Return 24 h rain measures."""
        return self.get_accessory_data(ACCESSORY_RAIN_24H_TYPE)

    def get_latest_pressures(self) -> dict[str, Any]:
        """Return latest pressure measures."""
        return self.get_latest_station_measures(STATION_PRESSURE_TYPE)

    def get_latest_temperatures(self) -> dict[str, Any]:
        """Return latest temperature measures."""
        return self.get_latest_station_measures(STATION_TEMPERATURE_TYPE)

    def get_latest_humidities(self) -> dict[str, Any]:
        """Return latest humidity measures."""
        return self.get_latest_station_measures(STATION_HUMIDITY_TYPE)

    def get_latest_wind_strengths(self) -> dict[str, Any]:
        """Return latest wind strength measures."""
        return self.get_accessory_data(ACCESSORY_WIND_STRENGTH_TYPE)

    def get_latest_wind_angles(self) -> dict[str, Any]:
        """Return latest wind angle measures."""
        return self.get_accessory_data(ACCESSORY_WIND_ANGLE_TYPE)

    def get_latest_gust_strengths(self) -> dict[str, Any]:
        """Return latest gust strength measures."""
        return self.get_accessory_data(ACCESSORY_GUST_STRENGTH_TYPE)

    def get_latest_gust_angles(self) -> dict[str, Any]:
        """Return latest gust angle measures."""

        return self.get_accessory_data(ACCESSORY_GUST_ANGLE_TYPE)

    def get_latest_station_measures(self, data_type: str) -> dict[str, Any]:
        """Return latest station measures of a given type."""

        measures: dict[str, Any] = {}
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
        """Return accessory data of a given type."""

        data: dict[str, Any] = {}
        for station in self.modules:
            for module in station["measures"].values():
                if data_type in module:
                    data[station["_id"]] = module[data_type]

        return data
