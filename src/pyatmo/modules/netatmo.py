"""Module to represent Netatmo modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    BatteryMixin,
    BoilerMixin,
    CameraMixin,
    FirmwareMixin,
    FloodlightMixin,
    NetatmoModule,
    RfMixin,
    WifiMixin,
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


class NACamera(FirmwareMixin, CameraMixin, WifiMixin, NetatmoModule):
    ...


class NOC(FloodlightMixin, FirmwareMixin, CameraMixin, WifiMixin, NetatmoModule):
    ...


class NDB(FirmwareMixin, NetatmoModule):
    ...


class NAMain(FirmwareMixin, NetatmoModule):
    ...


class NAModule1(FirmwareMixin, NetatmoModule):
    ...


class NAModule2(FirmwareMixin, NetatmoModule):
    ...


class NAModule3(FirmwareMixin, NetatmoModule):
    ...


class NAModule4(FirmwareMixin, NetatmoModule):
    ...
