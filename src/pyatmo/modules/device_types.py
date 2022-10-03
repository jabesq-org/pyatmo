"""Definitions of Netatmo devices types."""
from __future__ import annotations

import logging
from enum import Enum

LOG = logging.getLogger(__name__)

# pylint: disable=W0613


class DeviceType(str, Enum):
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
    NACamDoorTag = "NACamDoorTag"  # Smart Door and Window Sensors
    NACamera = "NACamera"  # Smart Indoor Camera
    NCO = "NCO"  # Smart Carbon Monoxide Alarm
    NDB = "NDB"  # Smart Video Doorbell
    NIS = "NIS"  # Smart Indoor Siren
    NOC = "NOC"  # Smart Outdoor Camera (with Siren)
    NSD = "NSD"  # Smart Smoke Detector

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
    NLC = "NLC"  # Cable outlet
    NLE = "NLE"  # Connected Ecometer
    NLF = "NLF"  # 2 wire light switch
    NLFN = "NLFN"  # light switch with neutral
    NLG = "NLG"  # Gateway
    NLGS = "NLGS"  # Gateway standalone
    NLIS = "NLIS"  # Double light switch
    NLL = "NLL"  # Italian light switch with neutral
    NLLM = "NLLM"  # Legrand / BTicino shutters
    NLLV = "NLLV"  # Legrand / BTicino shutters
    NLM = "NLM"  # light micro module
    NLP = "NLP"  # Plug
    NLPBS = "NLPBS"  # British standard plugs
    NLPC = "NLPC"  # Connected energy meter
    NLPM = "NLPM"  # mobile plug
    NLPO = "NLPO"  # Connected contactor
    NLPS = "NLPS"  # Smart Load Shedder
    NLPT = "NLPT"  # Connected latching relay / Telerupt
    NLT = "NLT"  # Global remote control
    NLV = "NLV"  # Legrand / BTicino shutters

    # BTicino Classe 300 EOS
    BNCX = "BNCX"  # internal panel = gateway
    BNDL = "BNDL"  # door lock
    BNEU = "BNEU"  # external unit
    BNSL = "BNSL"  # staircase light

    # Bubbendorf shutters
    NBG = "NBG"  # gateway
    NBO = "NBO"  # orientable shutter
    NBR = "NBR"  # roller shutter
    NBS = "NBS"  # swing shutter

    # pylint: enable=C0103


class DeviceCategory(str, Enum):
    """Class to represent Netatmo device types."""

    # temporarily disable locally-disabled and locally-enabled
    # pylint: disable=C0103

    climate = "climate"
    camera = "camera"
    siren = "siren"
    shutter = "shutter"
    lock = "lock"
    switch = "switch"
    sensor = "sensor"
    weather = "weather"
    air_care = "air_care"
    meter = "meter"
    dimmer = "dimmer"

    # pylint: enable=C0103


DEVICE_CATEGORY_MAP: dict[DeviceType, DeviceCategory] = {
    DeviceType.NRV: DeviceCategory.climate,
    DeviceType.NATherm1: DeviceCategory.climate,
    DeviceType.OTM: DeviceCategory.climate,
    DeviceType.NOC: DeviceCategory.camera,
    DeviceType.NACamera: DeviceCategory.camera,
    DeviceType.NDB: DeviceCategory.camera,
    DeviceType.NAMain: DeviceCategory.weather,
    DeviceType.NAModule1: DeviceCategory.weather,
    DeviceType.NAModule2: DeviceCategory.weather,
    DeviceType.NAModule3: DeviceCategory.weather,
    DeviceType.NAModule4: DeviceCategory.weather,
    DeviceType.NHC: DeviceCategory.air_care,
    DeviceType.NLV: DeviceCategory.shutter,
    DeviceType.NLLV: DeviceCategory.shutter,
    DeviceType.NLLM: DeviceCategory.shutter,
    DeviceType.NBR: DeviceCategory.shutter,
    DeviceType.NLP: DeviceCategory.switch,
    DeviceType.NLPM: DeviceCategory.switch,
    DeviceType.NLPBS: DeviceCategory.switch,
    DeviceType.NLIS: DeviceCategory.switch,
    DeviceType.NLL: DeviceCategory.switch,
    DeviceType.NLFN: DeviceCategory.dimmer,
    DeviceType.NLF: DeviceCategory.dimmer,
    DeviceType.BNS: DeviceCategory.climate,
    DeviceType.NLPC: DeviceCategory.meter,
    DeviceType.NLE: DeviceCategory.meter,
}


DEVICE_DESCRIPTION_MAP: dict[DeviceType, tuple[str, str]] = {
    # Climate/Energy
    DeviceType.NAPlug: ("Netatmo", "Smart Thermostat Gateway"),
    DeviceType.NATherm1: ("Netatmo", "Smart Thermostat"),
    DeviceType.NRV: ("Netatmo", "Smart Valve"),
    DeviceType.OTH: ("Netatmo", "OpenTherm Gateway"),
    DeviceType.OTM: ("Netatmo", "OpenTherm Modulating Thermostat"),
    # Cameras/Security,
    DeviceType.NOC: ("Netatmo", "Smart Outdoor Camera"),
    DeviceType.NACamera: ("Netatmo", "Smart Indoor Camera"),
    DeviceType.NSD: ("Netatmo", "Smart Smoke Detector"),
    DeviceType.NIS: ("Netatmo", "Smart Indoor Siren"),
    DeviceType.NACamDoorTag: ("Netatmo", "Smart Door/Window Sensors"),
    DeviceType.NDB: ("Netatmo", "Smart Video Doorbell"),
    DeviceType.NCO: ("Netatmo", "Smart Carbon Monoxide Alarm"),
    # Weather,
    DeviceType.NAMain: ("Netatmo", "Smart Home Weather station"),
    DeviceType.NAModule1: ("Netatmo", "Smart Outdoor Module"),
    DeviceType.NAModule2: ("Netatmo", "Smart Anemometer"),
    DeviceType.NAModule3: ("Netatmo", "Smart Rain Gauge"),
    DeviceType.NAModule4: ("Netatmo", "Smart Indoor Module"),
    DeviceType.public: ("Netatmo", "Public Weather station"),
    # Home Coach,
    DeviceType.NHC: ("Netatmo", "Smart Indoor Air Quality Monitor"),
    # 3rd Party,
    DeviceType.BNS: ("Smarther", "Smarther with Netatmo"),
    # Legrand Wiring devices and electrical panel products,
    DeviceType.NLG: ("Legrand", "Gateway"),
    DeviceType.NLGS: ("Legrand", "Gateway standalone"),
    DeviceType.NLP: ("Legrand", "Plug"),
    DeviceType.NLPM: ("Legrand", "Mobile plug"),
    DeviceType.NLPBS: ("Legrand", "British standard plugs"),
    DeviceType.NLF: ("Legrand", "2 wire light switch/dimmer"),
    DeviceType.NLIS: ("Legrand", "Double switch"),
    DeviceType.NLFN: ("Legrand", "Light switch/dimmer with neutral"),
    DeviceType.NLM: ("Legrand", "Light micro module"),
    DeviceType.NLL: ("Legrand", "Italian light switch with neutral"),
    DeviceType.NLV: ("Legrand/BTicino", "Shutters"),
    DeviceType.NLLV: ("Legrand/BTicino", "Shutters"),
    DeviceType.NLLM: ("Legrand/BTicino", "Shutters"),
    DeviceType.NLPO: ("Legrand", "Connected Contactor"),
    DeviceType.NLPT: ("Legrand", "Connected Latching Relay"),
    DeviceType.NLPC: ("Legrand", "Connected Energy Meter"),
    DeviceType.NLE: ("Legrand", "Connected Ecometer"),
    DeviceType.NLPS: ("Legrand", "Smart Load Shedder"),
    DeviceType.NLC: ("Legrand", "Cable Outlet"),
    DeviceType.NLT: ("Legrand", "Global Remote Control"),
    # BTicino Classe 300 EOS,
    DeviceType.BNCX: ("BTicino", "Internal Panel"),
    DeviceType.BNEU: ("BTicino", "External Unit"),
    DeviceType.BNDL: ("BTicino", "Door Lock"),
    DeviceType.BNSL: ("BTicino", "Staircase Light"),
    # Bubbendorf shutters,
    DeviceType.NBG: ("Bubbendorf", "Gateway"),
    DeviceType.NBR: ("Bubbendorf", "Roller Shutter"),
    DeviceType.NBO: ("Bubbendorf", "Orientable Shutter"),
    DeviceType.NBS: ("Bubbendorf", "Swing Shutter"),
}
