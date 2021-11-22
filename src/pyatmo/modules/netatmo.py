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


class NACamera(NetatmoModule):
    pass
