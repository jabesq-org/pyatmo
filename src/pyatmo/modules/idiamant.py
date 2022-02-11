"""Module to represent iDiamant modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    FirmwareMixin,
    NetatmoModule,
    RfMixin,
    ShutterMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)


class NBG(FirmwareMixin, WifiMixin, NetatmoModule):
    ...


class NBR(FirmwareMixin, RfMixin, ShutterMixin, NetatmoModule):
    ...
