"""Module to represent Smarther modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import Module, WifiMixin, FirmwareMixin, BoilerMixin

LOG = logging.getLogger(__name__)


class BNS(FirmwareMixin, BoilerMixin, WifiMixin, Module):
    """Smarther thermostat."""

    ...
