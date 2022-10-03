"""Module to represent Legrand modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    Dimmer,
    EnergyMixin,
    FirmwareMixin,
    HistoryMixin,
    Module,
    PowerMixin,
    RfMixin,
    ShutterMixin,
    Switch,
    SwitchMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)

# pylint: disable=R0901


class NLG(FirmwareMixin, Module):
    """Legrand gateway."""


class NLT(FirmwareMixin, Module):
    """Legrand global remote control."""


class NLP(Switch):
    """Legrand plug."""


class NLPM(Switch):
    """Legrand mobile plug."""


class NLPT(Switch):
    """Legrand latching relay/teleruptor."""


class NLPBS(Switch):
    """Legrand british standard plug."""


class NLF(Dimmer):
    """Legrand 2 wire light switch."""


class NLFN(Dimmer):
    """Legrand light switch with neutral."""


class NLM(Switch):
    """Legrand light micro module."""


class NLIS(Switch):
    """Legrand double switch."""


class NLL(FirmwareMixin, EnergyMixin, WifiMixin, SwitchMixin, Module):
    """Legrand / BTicino italian light switch with neutral."""


class NLV(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""


class NLLV(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""


class NLLM(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""


class NLPC(FirmwareMixin, HistoryMixin, PowerMixin, EnergyMixin, Module):
    """Legrand / BTicino connected energy meter."""


class NLE(FirmwareMixin, HistoryMixin, PowerMixin, EnergyMixin, Module):
    """Legrand / BTicino connected ecometer."""


class NLPS(FirmwareMixin, PowerMixin, EnergyMixin, Module):
    """Legrand / BTicino smart load shedder."""


class NLC(FirmwareMixin, SwitchMixin, Module):
    """Legrand / BTicino cable outlet."""
