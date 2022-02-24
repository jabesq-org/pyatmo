"""Module to represent iDiamant modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    FirmwareMixin,
    Module,
    RfMixin,
    ShutterMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)


class NBG(FirmwareMixin, WifiMixin, Module):
    ...


class NBR(FirmwareMixin, RfMixin, ShutterMixin, Module):
    ...
