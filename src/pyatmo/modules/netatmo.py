"""Module to represent Netatmo modules."""
from __future__ import annotations

import logging

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


class NACamera(FirmwareMixin, MonitoringMixin, CameraMixin, WifiMixin, NetatmoModule):
    ...


class NOC(
    FloodlightMixin,
    FirmwareMixin,
    MonitoringMixin,
    CameraMixin,
    WifiMixin,
    NetatmoModule,
):
    ...


class NDB(FirmwareMixin, NetatmoModule):
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
