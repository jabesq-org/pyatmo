"""Module to represent a Netatmo module."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyatmo.modules.base_class import EntityBase, NetatmoBase
from pyatmo.modules.device_types import NetatmoDeviceType

if TYPE_CHECKING:
    from pyatmo.home import NetatmoHome

LOG = logging.getLogger(__name__)


class WifiMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.wifi_strength: int | None = None


class RfMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.rf_strength: int | None = None


class BoilerMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.boiler_status: bool | None = None


class BatteryMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.battery_state: str | None = None
        self.battery_level: int | None = None


class ShutterMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.current_position: str | None = None
        self.target_position: str | None = None

    async def async_open(self) -> bool:
        """Open shutter."""
        json_open_roller_shutter = {
            "modules": [
                {
                    "id": self.entity_id,
                    "target_position": 100,
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_open_roller_shutter)


@dataclass
class NetatmoModule(NetatmoBase):
    """Class to represent a Netatmo module."""

    device_type: NetatmoDeviceType
    room_id: str | None

    modules: list[str] | None
    reachable: bool = False

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
