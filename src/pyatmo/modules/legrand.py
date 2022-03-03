"""Module to represent Legrand modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    EnergyMixin,
    FirmwareMixin,
    Module,
    Plug,
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


class NLP(Plug):
    """Legrand plug."""

    ...


class NLPM(Plug):
    """Legrand mobile plug."""

    ...


class NLPBS(Plug):
    """Legrand british standard plug."""

    ...


class NLF(Plug):
    """Legrand 2 wire light switch."""

    ...


class NLFN(Plug):
    """Legrand light switch with neutral."""

    ...


class NLM(Plug):
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
