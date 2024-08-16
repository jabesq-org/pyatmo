"""Base class for Netatmo entities."""

from __future__ import annotations

from abc import ABC
import bisect
from collections.abc import Iterable
from dataclasses import dataclass
import logging
from operator import itemgetter
from typing import TYPE_CHECKING, Any

from pyatmo.const import RawData
from pyatmo.modules.device_types import DeviceType

if TYPE_CHECKING:
    from pyatmo.event import EventTypes
    from pyatmo.home import Home

from time import time

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
    "target_position__step": lambda x, _: x.get("target_position:step"),
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
    history_features: set[str]
    history_features_values: dict[str, [int, int]] | {}
    name: str | None


# 2 days of dynamic historical data stored
MAX_HISTORY_TIME_FRAME = 24 * 2 * 3600


class NetatmoBase(EntityBase, ABC):
    """Base class for Netatmo entities."""

    def __init__(self, raw_data: RawData) -> None:
        """Initialize a Netatmo entity."""

        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", f"Unknown {self.entity_id}")
        self.history_features_values = {}
        self.history_features = set()

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

        now = int(time())
        for hist_feature in self.history_features:
            if hist_feature in self.__dict__:
                val = getattr(self, hist_feature)
                if val is None:
                    continue

                self.add_history_data(hist_feature, val, now)


    def add_history_data(self, feature: str, value, time: int) -> None:
        """Add historical data at the given time."""

        # get the feature values rolling buffer
        hist_f = self.history_features_values.setdefault(feature, [])
        if not hist_f or hist_f[-1][0] <= time:
            hist_f.append((time, value, self.entity_id))
        else:
            i = bisect.bisect_left(hist_f, time, key=itemgetter(0))

            if i < len(hist_f):
                if hist_f[i][0] == time:
                    hist_f[i] = (time, value, self.entity_id)
                    i = None

            if i is not None:
                hist_f.insert(i, (time, value, self.entity_id))

        # keep timing history to a maximum representative time
        while len(hist_f) > 0 and hist_f[-1][0] - hist_f[0][0] > MAX_HISTORY_TIME_FRAME:
            hist_f.pop(0)

    def get_history_data(self, feature: str, from_ts: int, to_ts: int | None = None):
        """Retrieve historical data."""

        hist_f = self.history_features_values.get(feature, [])

        if not hist_f:
            return []

        in_s = bisect.bisect_left(hist_f, from_ts, key=itemgetter(0))

        if to_ts is None:
            out_s = len(hist_f)
        else:
            out_s = bisect.bisect_right(hist_f, to_ts, key=itemgetter(0))

        return hist_f[in_s:out_s]


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
