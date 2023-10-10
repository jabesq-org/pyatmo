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
    """Class to represent a iDiamant NBG."""

    ...


class NBR(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Class to represent a iDiamant NBR."""

    ...


class NBO(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Class to represent a iDiamant NBO."""

    ...


class NBS(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Class to represent a iDiamant NBS."""

    ...
