"""Module to represent a Netatmo room."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyatmo.modules.base_class import NetatmoBase
from pyatmo.modules.device_types import NetatmoDeviceType

if TYPE_CHECKING:
    from .home import NetatmoHome
    from .modules.module import NetatmoModule

LOG = logging.getLogger(__name__)


@dataclass
class NetatmoRoom(NetatmoBase):
    """Class to represent a Netatmo room."""

    home: NetatmoHome
    modules: dict[str, NetatmoModule]
    device_type: NetatmoDeviceType | None = None

    reachable: bool = False
    therm_setpoint_temperature: float | None = None
    therm_setpoint_mode: str | None = None
    therm_measured_temperature: float | None = None
    heating_power_request: int | None = None

    def __init__(
        self,
        home: NetatmoHome,
        room: dict,
        all_modules: dict[str, NetatmoModule],
    ) -> None:
        super().__init__(room)
        self.home = home
        self.modules = {
            m_id: m
            for m_id, m in all_modules.items()
            if m_id in room.get("module_ids", [])
        }
        self.evaluate_device_type()

    def update_topology(self, raw_data: dict) -> None:
        self.name = raw_data["name"]
        self.modules = {
            m_id: m
            for m_id, m in self.home.modules.items()
            if m_id in raw_data.get("module_ids", [])
        }
        self.evaluate_device_type()

    def evaluate_device_type(self) -> None:
        for module in self.modules.values():
            if module.device_type in [
                NetatmoDeviceType.NATherm1,
                NetatmoDeviceType.NRV,
            ]:
                self.device_type = module.device_type
                break

    def update(self, raw_data: dict) -> None:
        self.reachable = raw_data.get("reachable", False)
        self.therm_measured_temperature = raw_data.get("therm_measured_temperature")
        self.therm_setpoint_mode = raw_data.get("therm_setpoint_mode")
        self.therm_setpoint_temperature = raw_data.get("therm_setpoint_temperature")
        self.heating_power_request = raw_data.get("heating_power_request")
