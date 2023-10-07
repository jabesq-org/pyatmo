"""Module to represent BTicino modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import Module, Switch

LOG = logging.getLogger(__name__)


class BNDL(Module):
    """BTicino door lock."""


class BNSL(Switch):  # pylint: disable=too-many-ancestors
    """BTicino staircase light."""


class BNCX(Module):
    """BTicino internal panel = gateway."""


class BNEU(Module):
    """BTicino external unit."""


class BNCS(Module):
    """BTicino camera."""
