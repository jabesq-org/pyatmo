"""Module to represent a Netatmo home."""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Callable

from . import module as netatmo_modules
from .auth import AbstractAsyncAuth
from .const import _GETHOMESDATA_REQ
from .helpers import extract_raw_data_new
from .room import NetatmoRoom
from .schedule import NetatmoSchedule


@dataclass
class NetatmoHome:
    """Class to represent a Netatmo home."""

    entity_id: str
    name: str
    rooms: dict[str, NetatmoRoom]
    modules: dict[str, netatmo_modules.NetatmoModule]
    schedules: dict[str, NetatmoSchedule]

    def __init__(self, raw_data: dict) -> None:
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", "Unknown")
        self.modules = {
            module["id"]: getattr(netatmo_modules, module["type"])(
                home=self,
                module=module,
            )
            for module in raw_data.get("modules", [])
        }
        self.rooms = {
            room["id"]: NetatmoRoom(
                home=self,
                room=room,
                all_modules=self.modules,
            )
            for room in raw_data.get("rooms", [])
        }
        self.schedules = {
            s["id"]: NetatmoSchedule(home=self, raw_data=s)
            for s in raw_data.get("schedules", [])
        }

    def update_topology(self, raw_data: dict) -> None:
        self.name = raw_data.get("name", "Unknown")

        raw_modules = raw_data.get("modules", [])
        for module in raw_modules:
            if (module_id := module["id"]) not in self.modules:
                self.modules[module_id] = getattr(netatmo_modules, module["type"])(
                    home=self,
                    module=module,
                )
            else:
                self.modules[module_id].update_topology(module)

        # Drop module if has been removed
        for module in self.modules.keys() - {m["id"] for m in raw_modules}:
            self.modules.pop(module)

        raw_rooms = raw_data.get("rooms", [])
        for room in raw_rooms:
            if (room_id := room["id"]) not in self.rooms:
                self.rooms[room_id] = NetatmoRoom(
                    home=self,
                    room=room,
                    all_modules=self.modules,
                )
            else:
                self.rooms[room_id].update_topology(room)

        # Drop room if has been removed
        for room in self.rooms.keys() - {m["id"] for m in raw_rooms}:
            self.rooms.pop(room)

        self.schedules = {
            s["id"]: NetatmoSchedule(home=self, raw_data=s)
            for s in raw_data.get("schedules", [])
        }

    def update(self, raw_data: dict) -> None:
        for module in raw_data["errors"]:
            self.modules[module["id"]].update({})

        data = raw_data["home"]

        for module in data.get("modules", []):
            self.modules[module["id"]].update(module)

        for room in data.get("rooms", []):
            self.rooms[room["id"]].update(room)

    def get_selected_schedule(self) -> NetatmoSchedule | None:
        """Return selected schedule for given home."""
        for schedule in self.schedules.values():
            if schedule.selected:
                return schedule
        return None

    def is_valid_schedule(self, schedule_id: str) -> bool:
        """Check if valid schedule."""
        return schedule_id in self.schedules

    def get_hg_temp(self) -> float | None:
        """Return frost guard temperature value for given home."""
        if (schedule := self.get_selected_schedule()) is None:
            return None
        return schedule.hg_temp

    def get_away_temp(self) -> float | None:
        """Return configured away temperature value for given home."""
        if (schedule := self.get_selected_schedule()) is None:
            return None
        return schedule.away_temp


class AbstractClimateTopology(ABC):
    """Abstract class of Netatmo energy device topology."""

    home_ids: list[str] = []
    subscriptions: dict[str, Callable] = {}
    raw_data: dict = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(home_ids={self.home_ids}, subscriptions={self.subscriptions})"

    def register_handler(self, home_id: str, handler: Callable) -> None:
        """Register update handler."""
        if self.subscriptions.get(home_id) == handler:
            return

        if home_id in self.subscriptions and self.subscriptions[home_id] != handler:
            self.unregister_handler(home_id)

        self.subscriptions[home_id] = handler

        self.publish()

    def unregister_handler(self, home_id: str) -> None:
        """Unregister update handler."""
        self.subscriptions.pop(home_id)

    def publish(self) -> None:
        """Publish latest data to subscribers."""
        for home in self.raw_data.get("homes", []):
            if (home_id := home["id"]) in self.subscriptions:
                self.subscriptions[home_id](home)


class AsyncClimateTopology(AbstractClimateTopology):
    """Async class of Netatmo energy device topology."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth

    async def async_update(self) -> None:
        """Retrieve status updates from /homesdata."""
        resp = await self.auth.async_post_request(url=_GETHOMESDATA_REQ)
        self.raw_data = extract_raw_data_new(await resp.json(), "homes")

        for home in self.raw_data["homes"]:
            self.home_ids.append(home["id"])

        self.publish()
