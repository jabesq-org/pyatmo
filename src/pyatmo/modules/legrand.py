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

# pylint: disable=R0901


class NLG(FirmwareMixin, NetatmoModule):
    """Legrand gateway."""

    ...


class NLT(FirmwareMixin, NetatmoModule):
    """Legrand global remote control."""

    ...


class NLP(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand plug."""

    ...


class NLPM(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand mobile plug."""

    ...


class NLPBS(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand british standard plug."""

    ...


class NLF(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand 2 wire light switch."""

    ...


class NLFN(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand light switch with neutral."""

    ...


class NLM(FirmwareMixin, EnergyMixin, SwitchMixin, NetatmoModule):
    """Legrand light micro module."""

    ...


class NLL(FirmwareMixin, EnergyMixin, WifiMixin, SwitchMixin, NetatmoModule):
    """Legrand / BTicino italian light switch with neutral."""

    ...


class NLV(FirmwareMixin, RfMixin, ShutterMixin, NetatmoModule):
    """Legrand / BTicino shutters."""

    ...


class NLLV(FirmwareMixin, RfMixin, ShutterMixin, NetatmoModule):
    """Legrand / BTicino shutters."""

    ...


class NLLM(FirmwareMixin, RfMixin, ShutterMixin, NetatmoModule):
    """Legrand / BTicino shutters."""

    ...


class NLPC(FirmwareMixin, EnergyMixin, NetatmoModule):
    """Legrand / BTicino connected energy meter."""

    ...


class NLE(FirmwareMixin, EnergyMixin, NetatmoModule):
    """Legrand / BTicino connected ecometer."""

    ...


class NLPS(FirmwareMixin, EnergyMixin, NetatmoModule):
    """Legrand / BTicino smart load shedder."""

    ...


class NLC(FirmwareMixin, SwitchMixin, NetatmoModule):
    """Legrand / BTicino cable outlet."""

    ...
