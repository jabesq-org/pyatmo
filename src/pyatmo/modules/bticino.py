"""Module to represent BTicino modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import NetatmoModule, SwitchMixin

LOG = logging.getLogger(__name__)


class BNDL(NetatmoModule):
    """BTicino door lock."""

    ...


class BNSL(SwitchMixin, NetatmoModule):
    """BTicino staircase light."""

    ...
