"""Module to represent BTicino modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import Module, SwitchMixin

LOG = logging.getLogger(__name__)


class BNDL(Module):
    """BTicino door lock."""

    ...


class BNSL(SwitchMixin, Module):
    """BTicino staircase light."""

    ...
