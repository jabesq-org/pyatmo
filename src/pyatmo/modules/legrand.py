"""Module to represent Legrand modules."""

from __future__ import annotations

import logging

from pyatmo.modules.module import (
    BatteryMixin,
    ContactorMixin,
    DimmableMixin,
    Dimmer,
    EnergyHistoryMixin,
    Fan,
    FirmwareMixin,
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


class NLT(DimmableMixin, FirmwareMixin, BatteryMixin, SwitchMixin, Module):
    """Legrand global remote control...but also wireless switch, like NLD"""


class NLP(Switch, OffloadMixin):
    """Legrand plug."""


class NLPM(Switch, OffloadMixin):
    """Legrand mobile plug."""


class NLPO(ContactorMixin, OffloadMixin, Switch):
    """Legrand contactor."""


class NLPT(Switch, OffloadMixin):
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


class NLD(DimmableMixin, FirmwareMixin, BatteryMixin, SwitchMixin, Module):
    """Legrand Double On/Off dimmer remote. Wireless 2 button switch light"""


class NLL(Switch, WifiMixin):
    """Legrand / BTicino italian light switch with neutral."""


class NLV(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""


class NLLV(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""


class NLLM(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand / BTicino shutters."""


class NLPC(FirmwareMixin, EnergyHistoryMixin, PowerMixin, Module):
    """Legrand / BTicino connected energy meter."""


class NLE(FirmwareMixin, EnergyHistoryMixin, PowerMixin, Module):
    """Legrand / BTicino connected ecometer."""


class NLPS(FirmwareMixin, EnergyHistoryMixin, PowerMixin, Module):
    """Legrand / BTicino smart load shedder."""


class NLC(Switch, OffloadMixin):
    """Legrand / BTicino cable outlet."""


class NLDD(FirmwareMixin, Module):
    """Legrand NLDD dimmer remote control."""


class NLUP(Switch):
    """Legrand NLUP Power outlet."""


class NLAO(FirmwareMixin, SwitchMixin, Module):
    """Legrand wireless batteryless light switch."""


class NLUI(FirmwareMixin, SwitchMixin, Module):
    """Legrand NLUI in-wall switch."""


class NLUF(Dimmer):
    """Legrand NLUF device stub."""


class NLUO(Dimmer):
    """Legrand NLUO device stub."""


class NLLF(Fan, PowerMixin, EnergyHistoryMixin):
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


class NLPD(Switch, OffloadMixin):
    """NLPD dry contact."""


class NLJ(FirmwareMixin, RfMixin, ShutterMixin, Module):
    """Legrand garage door opener."""
