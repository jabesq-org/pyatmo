"""Base class for Netatmo entities."""

from __future__ import annotations

from abc import ABC
import bisect
from dataclasses import dataclass
import logging
from operator import itemgetter
from time import time
from typing import TYPE_CHECKING, Any

from pyatmo.const import GPS_COORDINATES_COUNT, MAX_HISTORY_TIME_FRAME, RawData
from pyatmo.event import EventTypes
from pyatmo.modules.device_types import (
    ApplianceType,
    BoilerControl,
    BoilerError,
    DeviceType,
    DhwControl,
    DoorTagCategory,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from pyatmo.home import Home
    from pyatmo.modules.module import ModuleT


LOG: logging.Logger = logging.getLogger(__name__)


def bridged_module_ids(raw_data: dict[str, Any], default: Any = None) -> Any:  # noqa: ANN401
    """Return the bridged-children module ids.

    The /homesdata schema documents this list as `module_bridged` in some
    variants and `modules_bridged` in others; the API spelling is unconfirmed.
    Both are read, and `modules_bridged` takes precedence when both are present.
    """
    return raw_data.get("modules_bridged", raw_data.get("module_bridged", default))


NETATMO_ATTRIBUTES_MAP: dict[str, Callable[[dict[str, Any], Any], Any]] = {
    "entity_id": lambda x, y: x.get("id", y),
    "modules": bridged_module_ids,
    "device_type": lambda x, y: DeviceType(x.get("type", y)),
    "event_type": lambda x, y: EventTypes(x.get("type", y)),
    # Keyed on the private attribute: an absent `reachable` key means the API
    # did not report it, not that the module is unreachable.
    "_reachable": lambda x, y: x.get("reachable", y),
    "monitoring": lambda x, _: x.get("monitoring", False) == "on",
    "battery_level": lambda x, _: x.get("battery_vp", x.get("battery_level")),
    "place": lambda x, y: Place(x["place"]) if isinstance(x.get("place"), dict) else y,
    "target_position__step": lambda x, _: x.get("target_position:step"),
    "appliance_type": lambda x, y: ApplianceType(x.get("appliance_type", y)),
    "doortag_category": lambda x, y: DoorTagCategory(x.get("category", y)),
    # Coerce only when present so absent fields keep their default (no spurious
    # "unknown" warning from Enum(None) on every non-OTH update).
    "boiler_control": lambda x, y: (
        BoilerControl(x["boiler_control"]) if "boiler_control" in x else y
    ),
    "boiler_error": lambda x, y: (
        BoilerError(x["boiler_error"]) if "boiler_error" in x else y
    ),
    "dhw_control": lambda x, y: (
        DhwControl(x["dhw_control"]) if "dhw_control" in x else y
    ),
}


def default(key: str, val: Any) -> Callable[[dict[str, Any], Any], Any]:  # noqa: ANN401
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
    history_features_values: dict
    name: str

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize the entity."""
        self.home = home
        self.entity_id = module.get("id", "")
        self.name = module.get("name", f"Unknown {self.entity_id}")
        self.bridge = None
        self.history_features = set()
        self.history_features_values = {}

    def has_feature(self, feature: str) -> bool:
        """Check if the entity has the given feature."""

        return hasattr(self, feature) or feature in self.history_features


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

    def add_history_data(
        self,
        feature: str,
        value: Any,  # noqa: ANN401
        time: int,
    ) -> None:
        """Add historical data at the given time."""

        # get the feature values rolling buffer
        hist_f = self.history_features_values.setdefault(feature, [])
        if not hist_f or hist_f[-1][0] <= time:
            hist_f.append((time, value, self.entity_id))
        else:
            i = bisect.bisect_left(hist_f, time, key=itemgetter(0))

            if i < len(hist_f) and hist_f[i][0] == time:
                hist_f[i] = (time, value, self.entity_id)
            else:
                hist_f.insert(i, (time, value, self.entity_id))

        # keep timing history to a maximum representative time
        while len(hist_f) > 0 and hist_f[-1][0] - hist_f[0][0] > MAX_HISTORY_TIME_FRAME:
            hist_f.pop(0)

    def get_history_data(
        self,
        feature: str,
        from_ts: float,
        to_ts: float | None = None,
    ) -> list[Any]:
        """Retrieve historical data."""

        hist_f = self.history_features_values.get(feature, [])

        if not hist_f:
            return []

        in_s: int = bisect.bisect_left(hist_f, from_ts, key=itemgetter(0))

        if to_ts is None:
            out_s: int = len(hist_f)
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

    def __iter__(self) -> Iterator[float]:
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
        data: dict[str, Any] | None,
    ) -> None:
        """Initialize self."""

        self.altitude = None
        self.city = None
        self.country = None
        self.timezone = None
        self.location = None

        if not isinstance(data, dict):
            LOG.debug("Place data is unknown")
            return

        self.altitude = data.get("altitude")
        self.city = data.get("city")
        self.country = data.get("country")
        self.timezone = data.get("timezone")

        try:
            location_data: list[float] = list(data.get("location") or [])
        except TypeError:
            location_data = []

        if len(location_data) != GPS_COORDINATES_COUNT:
            LOG.debug("Invalid location data: %s", data)
            return

        self.location = Location(location_data[0], location_data[1])
