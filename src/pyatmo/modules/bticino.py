"""Module to represent BTicino modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import Module, Switch

LOG = logging.getLogger(__name__)


class BNDL(Module):
    """BTicino door lock."""


class BNSL(Switch):  # pylint: disable=too-many-ancestors
    """BTicino staircase light."""
