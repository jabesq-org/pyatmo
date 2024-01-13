"""Module to represent BTicino modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import Dimmer, Module, Shutter, Switch

LOG = logging.getLogger(__name__)


class BNDL(Module):
    """BTicino door lock."""


class BNSL(Switch):  # pylint: disable=too-many-ancestors
    """BTicino staircase light."""


class BNCX(Module):
    """BTicino internal panel = gateway."""


class BNEU(Module):
    """BTicino external unit."""


class BNCS(Switch):
    """Bticino module Controlled Socket."""


class BNXM(Module):
    """BTicino X meter."""


class BNMS(Shutter):
    """BTicino motorized shade."""


class BNAS(Shutter):
    """BTicino automatic shutter."""


class BNAB(Shutter):
    """BTicino automatic blind."""


class BNMH(Module):
    """BTicino MyHome server."""


class BNTH(Module):
    """BTicino thermostat."""


class BNFC(Module):
    """BTicino fan coil."""


class BNTR(Module):
    """BTicino radiator thermostat."""


class BNIL(Switch):
    """BTicino itelligent light."""


class BNLD(Dimmer):
    """BTicino dimmer light."""
