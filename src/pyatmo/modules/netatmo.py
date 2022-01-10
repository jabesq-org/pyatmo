"""Module to represent Netatmo modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    BatteryMixin,
    BoilerMixin,
    NetatmoModule,
    RfMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)


class NRV(RfMixin, BatteryMixin, NetatmoModule):
    ...


class NATherm1(RfMixin, BatteryMixin, BoilerMixin, NetatmoModule):
    ...


class NAPlug(WifiMixin, NetatmoModule):
    ...


class OTH(WifiMixin, NetatmoModule):
    ...


class OTM(RfMixin, BatteryMixin, BoilerMixin, NetatmoModule):
    ...


class NACamera(NetatmoModule):
    ...


class NOC(NetatmoModule):
    ...


class NDB(NetatmoModule):
    ...


class NAMain(NetatmoModule):
    ...


class NAModule1(NetatmoModule):
    ...


class NAModule2(NetatmoModule):
    ...


class NAModule3(NetatmoModule):
    ...


class NAModule4(NetatmoModule):
    ...
