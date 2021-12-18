"""Module to represent Netatmo modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import BatteryMixin, BoilerMixin, NetatmoModule

LOG = logging.getLogger(__name__)


class NRV(BatteryMixin, NetatmoModule):
    pass


class NATherm1(BatteryMixin, BoilerMixin, NetatmoModule):
    pass


class NAPlug(NetatmoModule):
    pass


class OTH(NetatmoModule):
    pass


class OTM(BatteryMixin, BoilerMixin, NetatmoModule):
    pass


class NACamera(NetatmoModule):
    pass


class NOC(NetatmoModule):
    pass


class NDB(NetatmoModule):
    pass


class NAMain(NetatmoModule):
    pass


class NAModule1(NetatmoModule):
    pass


class NAModule2(NetatmoModule):
    pass


class NAModule3(NetatmoModule):
    pass


class NAModule4(NetatmoModule):
    pass
