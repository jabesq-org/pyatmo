"""Definitions of Netatmo devices types."""
from __future__ import annotations

import logging
from enum import Enum

LOG = logging.getLogger(__name__)

# pylint: disable=W0613,R0201


class NetatmoDeviceType(str, Enum):
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
    NCO = "NCO"  # Smart Carbon Monoxide Alarm

    # Weather
    NAMain = "NAMain"  # Smart Home Weather Station
    NAModule1 = "NAModule1"
    NAModule2 = "NAModule2"
    NAModule3 = "NAModule3"
    NAModule4 = "NAModule4"
    public = "public"

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


class NetatmoDeviceCategory(str, Enum):
    """Class to represent Netatmo device types."""

    # temporarily disable locally-disabled and locally-enabled
    # pylint: disable=C0103

    climate = "climate"
    camera = "camera"
    siren = "siren"
    shutter = "shutter"
    lock = "lock"
    plug = "plug"
    sensor = "sensor"

    # pylint: enable=C0103


DEVICE_CATEGORY_MAP: dict[NetatmoDeviceType, NetatmoDeviceCategory] = {
    NetatmoDeviceType.NRV: NetatmoDeviceCategory.climate,
    NetatmoDeviceType.NATherm1: NetatmoDeviceCategory.climate,
    NetatmoDeviceType.OTM: NetatmoDeviceCategory.climate,
    NetatmoDeviceType.NOC: NetatmoDeviceCategory.camera,
    NetatmoDeviceType.NACamera: NetatmoDeviceCategory.camera,
    NetatmoDeviceType.NDB: NetatmoDeviceCategory.camera,
}


DEVICE_DESCRIPTION_MAP: dict[NetatmoDeviceType, str] = {
    # Climate/Energy
    NetatmoDeviceType.NAPlug: "Smart Thermostat Gateway",
    NetatmoDeviceType.NATherm1: "Smart Thermostat",
    NetatmoDeviceType.NRV: "Smart Valve",
    NetatmoDeviceType.OTH: "OpenTherm Gateway",
    NetatmoDeviceType.OTM: "OpenTherm Modulating Thermostat",
    # Cameras/Security,
    NetatmoDeviceType.NOC: "Smart Outdoor Camera",
    NetatmoDeviceType.NACamera: "Smart Indoor Camera",
    NetatmoDeviceType.NSD: "Smart Smoke Detector",
    NetatmoDeviceType.NIS: "Smart Indoor Siren",
    NetatmoDeviceType.NACamDoorTag: "Smart Door/Window Sensors",
    NetatmoDeviceType.NDB: "Smart Video Doorbell",
    NetatmoDeviceType.NCO: "Smart Carbon Monoxide Alarm",
    # Weather,
    NetatmoDeviceType.NAMain: "Smart Home Weather station",
    NetatmoDeviceType.NAModule1: "Smart Outdoor Module",
    NetatmoDeviceType.NAModule2: "Smart Anemometer",
    NetatmoDeviceType.NAModule3: "Smart Rain Gauge",
    NetatmoDeviceType.NAModule4: "Smart Indoor Module",
    NetatmoDeviceType.public: "Public Weather station",
    # Home Coach,
    NetatmoDeviceType.NHC: "Smart Indoor Air Quality Monitor",
    # 3rd Party,
    NetatmoDeviceType.BNS: "Smarther with Netatmo",
    # Legrand Wiring devices and electrical panel products,
    NetatmoDeviceType.NLG: "Gateway",
    NetatmoDeviceType.NLGS: "Gateway standalone",
    NetatmoDeviceType.NLP: "Plug",
    NetatmoDeviceType.NLPM: "Mobile plug",
    NetatmoDeviceType.NLPBS: "British standard plugs",
    NetatmoDeviceType.NLF: "2 wire light switch",
    NetatmoDeviceType.NLFN: "Light switch with neutral",
    NetatmoDeviceType.NLM: "Light micro module",
    NetatmoDeviceType.NLL: "Italian light switch with neutral",
    NetatmoDeviceType.NLV: "Legrand/BTicino Shutters",
    NetatmoDeviceType.NLLV: "Legrand/BTicino Shutters",
    NetatmoDeviceType.NLLM: "Legrand/BTicino Shutters",
    NetatmoDeviceType.NLPO: "Connected Contactor",
    NetatmoDeviceType.NLPT: "Connected Latching Relay",
    NetatmoDeviceType.NLPC: "Connected Energy Meter",
    NetatmoDeviceType.NLE: "Connected Ecometer",
    NetatmoDeviceType.NLPS: "Smart Load Shedder",
    NetatmoDeviceType.NLC: "Cable Outlet",
    NetatmoDeviceType.NLT: "Global Remote Control",
    # BTicino Classe 300 EOS,
    NetatmoDeviceType.BNCX: "Internal Panel",
    NetatmoDeviceType.BNEU: "External Unit",
    NetatmoDeviceType.BNDL: "Door Lock",
    NetatmoDeviceType.BNSL: "Staircase Light",
    # Bubbendorf shutters,
    NetatmoDeviceType.NBG: "Gateway",
    NetatmoDeviceType.NBR: "Roller Shutter",
    NetatmoDeviceType.NBO: "Orientable Shutter",
    NetatmoDeviceType.NBS: "Swing Shutter",
}
