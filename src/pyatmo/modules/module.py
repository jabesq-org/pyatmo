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


class FirmwareMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.firmware_revision: int | None = None
        self.firmware_name: str | None = None


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

    async def async_set_target_position(self, target_position: int) -> bool:
        """Set shutter to target position."""
        json_roller_shutter = {
            "modules": [
                {
                    "id": self.entity_id,
                    "target_position": max(min(100, target_position), 0),
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_roller_shutter)

    async def async_open(self) -> bool:
        """Open shutter."""
        return await self.async_set_target_position(100)

    async def async_close(self) -> bool:
        """Close shutter."""
        return await self.async_set_target_position(0)


class CameraMixin(EntityBase):
    def __init__(self, home: NetatmoHome, module: dict):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.sd_status: int | None = None
        self.vpn_url: str | None = None
        self.is_local: bool | None = None
        self.monitoring: str | None = None
        self.alim_status: int | None = None


@dataclass
class NetatmoModule(NetatmoBase):
    """Class to represent a Netatmo module."""

    device_type: NetatmoDeviceType
    room_id: str | None

    modules: list[str] | None
    reachable: bool | None

    def __init__(self, home: NetatmoHome, module: dict) -> None:
        super().__init__(module)
        self.device_type = NetatmoDeviceType(module["type"])
        self.home = home
        self.room_id = module.get("room_id")
        self.reachable = module.get("reachable")
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
