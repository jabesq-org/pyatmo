"""Module to represent Legrand modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    EnergyMixin,
    FirmwareMixin,
    Module,
    RfMixin,
    ShutterMixin,
    SwitchMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)

# pylint: disable=R0901


class NLG(FirmwareMixin, Module):
    """Legrand gateway."""

    ...


class NLT(FirmwareMixin, Module):
    """Legrand global remote control."""

    ...


class NLP(FirmwareMixin, EnergyMixin, SwitchMixin, Module):
    """Legrand plug."""

    ...


class NLPM(FirmwareMixin, EnergyMixin, SwitchMixin, Module):
    """Legrand mobile plug."""

    ...


class NLPBS(FirmwareMixin, EnergyMixin, SwitchMixin, Module):
    """Legrand british standard plug."""

    ...


class NLF(FirmwareMixin, EnergyMixin, SwitchMixin, Module):
    """Legrand 2 wire light switch."""

    ...


class NLFN(FirmwareMixin, EnergyMixin, SwitchMixin, Module):
    """Legrand light switch with neutral."""

    ...


class NLM(FirmwareMixin, EnergyMixin, SwitchMixin, Module):
    """Legrand light micro module."""

    ...


class NLL(FirmwareMixin, EnergyMixin, WifiMixin, SwitchMixin, Module):
    """Legrand / BTicino italian light switch with neutral."""

    ...


class NLV(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""

    ...


class NLLV(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""

    ...


class NLLM(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""

    ...


class NLPC(FirmwareMixin, EnergyMixin, Module):
    """Legrand / BTicino connected energy meter."""

    ...


class NLE(FirmwareMixin, EnergyMixin, Module):
    """Legrand / BTicino connected ecometer."""

    ...


class NLPS(FirmwareMixin, EnergyMixin, Module):
    """Legrand / BTicino smart load shedder."""

    ...


class NLC(FirmwareMixin, SwitchMixin, Module):
    """Legrand / BTicino cable outlet."""

    ...
