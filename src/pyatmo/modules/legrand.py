"""Module to represent Legrand modules."""
from __future__ import annotations

import logging

from pyatmo.modules.module import (
    BatteryMixin,
    ContactorMixin,
    Dimmer,
    EnergyMixin,
    Fan,
    FirmwareMixin,
    HistoryMixin,
    Module,
    OffloadMixin,
    PowerMixin,
    RfMixin,
    ShutterMixin,
    Switch,
    SwitchMixin,
    WifiMixin,
)

LOG = logging.getLogger(__name__)

# pylint: disable=R0901


class NLG(FirmwareMixin, OffloadMixin, WifiMixin, Module):
    """Legrand gateway."""


class NLT(FirmwareMixin, BatteryMixin, Module):
    """Legrand global remote control."""


class NLP(Switch, HistoryMixin, PowerMixin, OffloadMixin, Module):
    """Legrand plug."""


class NLPM(Switch):
    """Legrand mobile plug."""


class NLPO(ContactorMixin, OffloadMixin, Switch):
    """Legrand contactor."""


class NLPT(Switch):
    """Legrand latching relay/teleruptor."""


class NLPBS(Switch):
    """Legrand british standard plug."""


class NLF(Dimmer):
    """Legrand 2 wire light switch."""


class NLFN(Dimmer):
    """Legrand light switch with neutral."""


class NLFE(Dimmer):
    """Legrand On-Off dimmer switch evolution."""


class NLM(Switch):
    """Legrand light micro module."""


class NLIS(Switch):
    """Legrand double switch."""


class NLD(Dimmer):
    """Legrand Double On/Off dimmer remote."""


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


class NLC(FirmwareMixin, SwitchMixin, HistoryMixin, PowerMixin, OffloadMixin, Module):
    """Legrand / BTicino cable outlet."""


class NLDD(FirmwareMixin, Module):
    """Legrand NLDD dimmer remote control."""


class NLUP(FirmwareMixin, PowerMixin, SwitchMixin, Module):
    """Legrand NLUP Power outlet."""


class NLAO(FirmwareMixin, SwitchMixin, Module):
    """Legrand wireless batteryless light switch."""


class NLUI(FirmwareMixin, SwitchMixin, Module):
    """Legrand NLUI in-wall switch."""


class NLUF(Dimmer):
    """Legrand NLUF device stub."""


class NLUO(Dimmer):
    """Legrand NLUO device stub."""


class NLLF(Fan):
    """Legrand NLLF fan/ventilation device."""


class NLunknown(Module):
    """NLunknown device stub."""


class NLAS(Module):
    """NLAS wireless batteryless scene switch."""


class Z3L(Dimmer):
    """Zigbee 3 Light."""


class EBU(Module):
    """EBU gas meter."""


class NLTS(Module):
    """NLTS motion sensor."""


class NLPD(FirmwareMixin, SwitchMixin, EnergyMixin, PowerMixin, Module):
    """NLPD dry contact."""


class NLJ(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand garage door opener."""
