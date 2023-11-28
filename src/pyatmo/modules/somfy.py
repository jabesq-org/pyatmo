"""Module to represent somfy modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import RfMixin, Shutter

LOG = logging.getLogger(__name__)


class TPSRS(RfMixin, Shutter):
    """Class to represent a somfy TPSRS."""

    ...
