"""Module to represent iDiamant modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import NetatmoModule, RfMixin, ShutterMixin, WifiMixin

LOG = logging.getLogger(__name__)


class NBG(WifiMixin, NetatmoModule):
    ...


class NBR(RfMixin, ShutterMixin, NetatmoModule):
    ...
