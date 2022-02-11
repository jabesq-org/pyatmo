"""Deifinitions of Netatmo devices types."""
from __future__ import annotations

import logging
from enum import Enum

LOG = logging.getLogger(__name__)

# pylint: disable=W0613,R0201


class NetatmoDeviceType(Enum):
    """Class to represent Netatmo device types."""

    # temporarily disable locally-disabled and locally-enabled
    # pylint: disable=C0103

    # Climate/Energy
    NAPlug = "NAPlug"  # Smart thermostat gateway
    NATherm1 = "NATherm1"  # Smart thermostat
    NRV = "NRV"  # Smart valve
    OTH = "OTH"  # OpenTherm gateway
    OTM = "OTM"  # OpenTherm modulating thermostat

    # Cameras/Security
    NOC = "NOC"  # Smart Outdoor Camera (with Siren)
    NACamera = "NACamera"  # Smart Indoor Camera
    NSD = "NSD"  # Smart Smoke Detector
    NIS = "NIS"  # Smart Indoor Siren
    NACamDoorTag = "NACamDoorTag"  # Smart Door and Window Sensors
    NDB = "NDB"  # Smart Video Doorbell
    NCO = "NCO"  # Smark Carbon Monoxide Alarm

    # Weather
    NAMain = "NAMain"  # Smart Home Weather Station
    NAModule1 = "NAModule1"
    NAModule2 = "NAModule2"
    NAModule3 = "NAModule3"
    NAModule4 = "NAModule4"

    # Home Coach
    NHC = "NHC"  # Smart Indoor Air Quality Monitor

    # 3rd Party
    BNS = "BNS"  # Smarther with Netatmo
    # Legrand Wiring devices and electrical panel products
    NLG = "NLG"  # Gateway
    NLGS = "NLGS"  # Gateway standalone
    NLP = "NLP"  # Plug
    NLPM = "NLPM"  # mobile plug
    NLPBS = "NLPBS"  # British standard plugs
    NLF = "NLF"  # 2 wire light switch
    NLFN = "NLFN"  # light switch with neutral
    NLM = "NLM"  # light micro module
    NLL = "NLL"  # Italian light switch with neutral
    NLV = "NLV"  # Legrand / BTicino shutters
    NLLV = "NLLV"  # Legrand / BTicino shutters
    NLLM = "NLLM"  # Legrand / BTicino shutters
    NLPO = "NLPO"  # Connected contactor
    NLPT = "NLPT"  # Connected latching relay / Telerupt
    NLPC = "NLPC"  # Connected energy meter
    NLE = "NLE"  # Connected Ecometer
    NLPS = "NLPS"  # Smart Load Shedder
    NLC = "NLC"  # Cable outlet
    NLT = "NLT"  # Global remote control

    # BTicino Classe 300 EOS
    BNCX = "BNCX"  # internal panel = gateway
    BNEU = "BNEU"  # external unit
    BNDL = "BNDL"  # door lock
    BNSL = "BNSL"  # staircase light

    # Bubbendorf shutters
    NBG = "NBG"  # gateway
    NBR = "NBR"  # roller shutter
    NBO = "NBO"  # orientable shutter
    NBS = "NBS"  # swing shutter

    # pylint: enable=C0103
