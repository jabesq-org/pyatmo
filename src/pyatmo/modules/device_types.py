"""Definitions of Netatmo devices types."""
from __future__ import annotations

import logging
from enum import Enum

LOG = logging.getLogger(__name__)

# pylint: disable=W0613,R0201


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


class DeviceCategory(str, Enum):
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
    weather = "weather"
    air_care = "air_care"
    meter = "meter"

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
    DeviceType.NLP: DeviceCategory.plug,
    DeviceType.NLPM: DeviceCategory.plug,
    DeviceType.NLPBS: DeviceCategory.plug,
    DeviceType.NLL: DeviceCategory.plug,
    DeviceType.NLFN: DeviceCategory.plug,
    DeviceType.NLF: DeviceCategory.plug,
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
    DeviceType.NLF: ("Legrand", "2 wire light switch"),
    DeviceType.NLFN: ("Legrand", "Light switch with neutral"),
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
