"""Base class for Netatmo entities."""
from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING

from pyatmo.modules.device_types import DeviceType

if TYPE_CHECKING:
    from pyatmo.event import EventTypes
    from pyatmo.home import Home

LOG = logging.getLogger(__name__)


NETATMO_ATTRIBUTES_MAP = {
    "entity_id": lambda x, y: x.get("id", y),
    "modules": lambda x, y: x.get("modules_bridged", y),
    "device_type": lambda x, y: DeviceType(x.get("type", y)),
    "event_type": lambda x, y: EventTypes(x.get("type", y)),
    "reachable": lambda x, _: x.get("reachable", False),
    "monitoring": lambda x, _: x.get("monitoring", False) == "on",
    "battery_level": lambda x, y: x.get("battery_vp", x.get("battery_level")),
}


def default(key, val):
    return lambda x, _: x.get(key, val)


class EntityBase:
    entity_id: str
    home: Home
    bridge: str | None


class NetatmoBase(EntityBase, ABC):
    """Base class for Netatmo entities."""

    def __init__(self, raw_data: dict) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", f"Unknown {self.entity_id}")

    def update_topology(self, raw_data: dict) -> None:
        self._update_attributes(raw_data)

        if (
            self.bridge
            and self.bridge in self.home.modules
            and getattr(self, "device_category") == "weather"
        ):
            self.name = f"{self.home.modules[self.bridge].name} {self.name}"

    def _update_attributes(self, raw_data: dict) -> None:
        self.__dict__ = {
            key: NETATMO_ATTRIBUTES_MAP.get(key, default(key, val))(raw_data, val)
            for key, val in self.__dict__.items()
        }
