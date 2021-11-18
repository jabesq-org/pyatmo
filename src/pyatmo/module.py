"""Module to represent a Netatmo module."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .device_types import NetatmoDeviceType

if TYPE_CHECKING:
    from .home import NetatmoHome

LOG = logging.getLogger(__name__)


@dataclass
class NetatmoModule:
    """Class to represent a Netatmo module."""

    entity_id: str
    name: str
    device_type: NetatmoDeviceType
    home: NetatmoHome
    room_id: str | None

    reachable: bool
    bridge: NetatmoModule | None
    modules: list[str]

    battery_state: str | None = None
    battery_level: int | None = None
    boiler_status: bool | None = None

    def __init__(self, home: NetatmoHome, module: dict) -> None:
        self.entity_id = module["id"]
        self.name = module.get("name", "Unkown")
        self.device_type = NetatmoDeviceType(module["type"])
        self.home = home
        self.room_id = module.get("room_id")
        self.reachable = False
        self.bridge = module.get("bridge")
        self.modules = module.get("modules_bridged", [])

    def update_topology(self, raw_data: dict) -> None:
        self.name = raw_data.get("name", "Unkown")
        self.device_type = NetatmoDeviceType(raw_data["type"])
        self.room_id = raw_data.get("room_id")
        self.bridge = raw_data.get("bridge")
        self.modules = raw_data.get("modules_bridged", [])

    def update(self, raw_data: dict) -> None:
        self.reachable = raw_data.get("reachable", False)
        self.boiler_status = raw_data.get("boiler_status")
        self.battery_level = raw_data.get("battery_level")
        self.battery_state = raw_data.get("battery_state")

        if not self.reachable:
            # Update bridged modules and associated rooms
            for module_id in self.modules:
                module = self.home.modules[module_id]
                module.update(raw_data)
                if module.room_id:
                    self.home.rooms[module.room_id].update(raw_data)
