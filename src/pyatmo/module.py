"""Module to represent a Netatmo module."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base_class import NetatmoBase
from .device_types import NetatmoDeviceType

if TYPE_CHECKING:
    from .home import NetatmoHome

LOG = logging.getLogger(__name__)


class MixinBase:
    def update_topology(self, raw_data: dict) -> None:
        pass


class BoilerMixin:
    boiler_status: bool | None = None


class BatteryMixin:
    battery_state: str | None = None
    battery_level: int | None = None


@dataclass
class NetatmoModule(NetatmoBase):
    """Class to represent a Netatmo module."""

    device_type: NetatmoDeviceType
    home: NetatmoHome
    room_id: str | None

    modules: list[str] | None
    reachable: bool = False
    bridge: NetatmoModule | None = None

    def __init__(self, home: NetatmoHome, module: dict) -> None:
        super().__init__(module)
        self.device_type = NetatmoDeviceType(module["type"])
        self.home = home
        self.room_id = module.get("room_id")
        self.reachable = False
        self.bridge = module.get("bridge")
        self.modules = module.get("modules_bridged")

    def update(self, raw_data: dict) -> None:
        self.update_topology(raw_data)

        if not self.reachable and self.modules:
            # Update bridged modules and associated rooms
            for module_id in self.modules:
                module = self.home.modules[module_id]
                module.update(raw_data)
                if module.room_id:
                    self.home.rooms[module.room_id].update(raw_data)


class NVAModule(BatteryMixin, BoilerMixin, NetatmoModule):
    pass
