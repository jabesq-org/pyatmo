"""Module to represent Smarther modules."""

from __future__ import annotations

import logging

from pyatmo.modules.module import (
    BoilerMixin,
    CoolerMixin,
    FirmwareMixin,
    Module,
    WifiMixin,
)

LOG = logging.getLogger(__name__)


class BNS(FirmwareMixin, BoilerMixin, CoolerMixin, WifiMixin, Module):
    """Smarther thermostat."""
