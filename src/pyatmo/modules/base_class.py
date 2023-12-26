"""Base class for Netatmo entities."""
from __future__ import annotations

from abc import ABC
from collections.abc import Iterable
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

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
    """Return default value."""

    return lambda x, _: x.get(key, val)


def update_name(name: str, pre_fix: str) -> str:
    """Remove duplicates from string."""

    if name.startswith(pre_fix):
        return name
    return f"{pre_fix} {name}"


class EntityBase:
    """Base class for Netatmo entities."""

    entity_id: str
    home: Home
    bridge: str | None


class NetatmoBase(EntityBase, ABC):
    """Base class for Netatmo entities."""

    def __init__(self, raw_data: RawData) -> None:
        """Initialize a Netatmo entity."""

        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", f"Unknown {self.entity_id}")

    def update_topology(self, raw_data: RawData) -> None:
        """Update topology."""

        self._update_attributes(raw_data)

        if (
            self.bridge
            and self.bridge in self.home.modules
            and getattr(self, "device_category") == "weather"
        ):
            self.name = update_name(self.name, self.home.modules[self.bridge].name)

    def _update_attributes(self, raw_data: RawData) -> None:
        """Update attributes."""

        self.__dict__ = {
            key: NETATMO_ATTRIBUTES_MAP.get(key, default(key, val))(raw_data, val)
            for key, val in self.__dict__.items()
        }


@dataclass
class Location:
    """Class of Netatmo public weather location."""

    latitude: float
    longitude: float

    def __init__(self, longitude: float, latitude: float) -> None:
        """Initialize self."""

        self.latitude = latitude
        self.longitude = longitude

    def __iter__(self) -> Iterable[float]:
        """Iterate over latitude and longitude."""

        yield self.longitude
        yield self.latitude


@dataclass
class Place:
    """Class of Netatmo public weather place."""

    altitude: int | None
    city: str | None
    country: str | None
    timezone: str | None
    location: Location | None

    def __init__(
        self,
        data: dict[str, Any],
    ) -> None:
        """Initialize self."""

        if data is None:
            return
        self.altitude = data.get("altitude")
        self.city = data.get("city")
        self.country = data.get("country")
        self.timezone = data.get("timezone")
        self.location = Location(*list(data.get("location", [])))
