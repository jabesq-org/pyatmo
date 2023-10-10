"""Module to represent somfy modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import FirmwareMixin, Module, RfMixin, ShutterMixin

LOG = logging.getLogger(__name__)


class TPSRS(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Class to represent a somfy TPSRS."""

    ...
