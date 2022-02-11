"""Module to represent Legrand modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    EnergyMixin,
    FirmwareMixin,
    NetatmoModule,
    RfMixin,
    ShutterMixin,
    SwitchMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)


class NLG(FirmwareMixin, NetatmoModule):
    """Legrand gateway."""

    ...


class NLT(FirmwareMixin, NetatmoModule):
    """Legrand global remote control."""

    ...


class NLP(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand plug."""

    ...


class NLPM(EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand mobile plug."""

    ...


class NLPBS(EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand british standard plug."""

    ...


class NLF(EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand 2 wire light switch."""

    ...


class NLFN(EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand light switch with neutral."""

    ...


class NLM(EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand light micro module."""

    ...


class NLL(EnergyMixin, WifiMixin, SwitchMixin, NetatmoModule):
    """Legrand / BTicino italian light switch with neutral."""

    ...


class NLV(RfMixin, ShutterMixin, NetatmoModule):
    """Legrand / BTicino shutters."""

    ...


class NLLV(RfMixin, ShutterMixin, NetatmoModule):
    """Legrand / BTicino shutters."""

    ...


class NLLM(RfMixin, ShutterMixin, NetatmoModule):
    """Legrand / BTicino shutters."""

    ...


class NLPC(EnergyMixin, NetatmoModule):
    """Legrand / BTicino connected energy meter."""

    ...


class NLE(EnergyMixin, NetatmoModule):
    """Legrand / BTicino connected ecometer."""

    ...


class NLPS(EnergyMixin, NetatmoModule):
    """Legrand / BTicino smart load shedder."""

    ...


class NLC(SwitchMixin, NetatmoModule):
    """Legrand / BTicino cable outlet."""

    ...
