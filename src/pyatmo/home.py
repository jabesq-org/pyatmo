"""Module to represent a Netatmo home."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyatmo import modules
from pyatmo.const import _SETTHERMMODE_REQ, _SWITCHHOMESCHEDULE_REQ
from pyatmo.exceptions import NoSchedule
from pyatmo.room import NetatmoRoom
from pyatmo.schedule import NetatmoSchedule

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


@dataclass
class NetatmoHome:
    """Class to represent a Netatmo home."""

    auth: AbstractAsyncAuth
    entity_id: str
    name: str
    rooms: dict[str, NetatmoRoom]
    modules: dict[str, modules.NetatmoModule]
    schedules: dict[str, NetatmoSchedule]

    def __init__(self, auth: AbstractAsyncAuth, raw_data: dict) -> None:
        self.auth = auth
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", "Unknown")
        self.modules = {
            module["id"]: getattr(modules, module["type"])(
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
                self.modules[module_id] = getattr(modules, module["type"])(
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

    async def async_set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> dict:
        """Set thermotat mode."""
        if schedule_id is not None and not self.is_valid_schedule(
            schedule_id,
        ):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id.")

        if mode is None:
            raise NoSchedule(f"{mode} is not a valid mode.")

        post_params = {"home_id": self.entity_id, "mode": mode}
        if end_time is not None and mode in {"hg", "away"}:
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        LOG.debug(
            "Setting home (%s) mode to %s (%s)",
            self.entity_id,
            mode,
            schedule_id,
        )

        resp = await self.auth.async_post_request(
            url=_SETTHERMMODE_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_switch_home_schedule(self, schedule_id: str) -> None:
        """Switch the schedule for a give home ID."""
        if not self.is_valid_schedule(schedule_id):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id")

        LOG.debug("Setting home (%s) schedule to %s", self.entity_id, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SWITCHHOMESCHEDULE_REQ,
            params={"home_id": self.entity_id, "schedule_id": schedule_id},
        )
        LOG.debug("Response: %s", resp)
