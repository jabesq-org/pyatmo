"""Base class for Netatmo entities."""
from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING

from pyatmo.modules.device_types import NetatmoDeviceType

if TYPE_CHECKING:
    from pyatmo.home import NetatmoHome

LOG = logging.getLogger(__name__)


NETATMO_ATTRIBUTES_MAP = {
    "entity_id": lambda x, y: x.get("id", y),
    "modules": lambda x, y: x.get("modules_bridged", y),
    "device_type": lambda x, y: NetatmoDeviceType(x.get("type", y)),
    "reachable": lambda x, _: x.get("reachable", False),
}


def default(key, val):
    return lambda x, _: x.get(key, val)


class EntityBase:
    entity_id: str
    home: NetatmoHome
    bridge: str | None


class NetatmoBase(EntityBase, ABC):
    """Base class for Netatmo entities."""

    def __init__(self, raw_data: dict) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", f"Unknown {self.entity_id}")

    def update_topology(self, raw_data: dict) -> None:
        self.__dict__ = {
            key: NETATMO_ATTRIBUTES_MAP.get(key, default(key, val))(raw_data, val)
            for key, val in self.__dict__.items()
        }
