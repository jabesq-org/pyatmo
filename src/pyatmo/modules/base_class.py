"""Base class for Netatmo entities."""
from __future__ import annotations

import logging
from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable

from pyatmo.const import RawData
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
    "place": lambda x, _: Place(x.get("place")),
}


def default(key: str, val: Any) -> Any:
    return lambda x, _: x.get(key, val)


class EntityBase:
    entity_id: str
    home: Home
    bridge: str | None


class NetatmoBase(EntityBase, ABC):
    """Base class for Netatmo entities."""

    def __init__(self, raw_data: RawData) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", f"Unknown {self.entity_id}")

    def update_topology(self, raw_data: RawData) -> None:
        self._update_attributes(raw_data)

        if (
            self.bridge
            and self.bridge in self.home.modules
            and getattr(self, "device_category") == "weather"
        ):
            self.name = f"{self.home.modules[self.bridge].name} {self.name}"

    def _update_attributes(self, raw_data: RawData) -> None:
        self.__dict__ = {
            key: NETATMO_ATTRIBUTES_MAP.get(key, default(key, val))(raw_data, val)
            for key, val in self.__dict__.items()
        }


@dataclass
class Location:
    latitude: float
    longitude: float

    def __init__(self, longitude: float, latitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude

    def __iter__(self) -> Iterable[float]:
        yield self.longitude
        yield self.latitude


@dataclass
class Place:
    altitude: int | None
    city: str | None
    country: str | None
    timezone: str | None
    location: Location | None

    def __init__(
        self,
        data: dict[str, Any],
    ) -> None:
        if data is None:
            return
        self.altitude = data.get("altitude")
        self.city = data.get("city")
        self.country = data.get("country")
        self.timezone = data.get("timezone")
        self.location = Location(*list(data.get("location", [])))
