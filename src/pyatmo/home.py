"""Module to represent a Netatmo home."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyatmo import modules
from pyatmo.const import (
    _SETPERSONSAWAY_REQ,
    _SETPERSONSHOME_REQ,
    _SETSTATE_REQ,
    _SETTHERMMODE_REQ,
    _SWITCHHOMESCHEDULE_REQ,
)
from pyatmo.exceptions import InvalidState, NoSchedule
from pyatmo.person import NetatmoPerson
from pyatmo.room import NetatmoRoom
from pyatmo.schedule import NetatmoSchedule

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


class NetatmoHome:
    """Class to represent a Netatmo home."""

    auth: AbstractAsyncAuth
    entity_id: str
    name: str
    rooms: dict[str, NetatmoRoom]
    modules: dict[str, modules.NetatmoModule]
    schedules: dict[str, NetatmoSchedule]
    persons: dict[str, NetatmoPerson]

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
        self.persons = {
            s["id"]: NetatmoPerson(home=self, raw_data=s)
            for s in raw_data.get("persons", [])
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

    async def update(self, raw_data: dict) -> None:
        for module in raw_data.get("errors", []):
            await self.modules[module["id"]].update({})

        data = raw_data["home"]

        for module in data.get("modules", []):
            await self.modules[module["id"]].update(module)

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
    ) -> bool:
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

        if (await resp.json()).get("status") == "ok":
            return True

        return False

    async def async_switch_schedule(self, schedule_id: str) -> bool:
        """Switch the schedule."""
        if not self.is_valid_schedule(schedule_id):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id")

        LOG.debug("Setting home (%s) schedule to %s", self.entity_id, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SWITCHHOMESCHEDULE_REQ,
            params={"home_id": self.entity_id, "schedule_id": schedule_id},
        )

        if (await resp.json()).get("status") == "ok":
            return True

        return False

    async def async_set_state(self, data: dict) -> bool:
        """Set state using given data."""
        if not is_valid_state(data):
            raise InvalidState("Data for '/set_state' contains errors.")

        LOG.debug("Setting state for home (%s) according to %s", self.entity_id, data)

        resp = await self.auth.async_post_request(
            url=_SETSTATE_REQ,
            params={"json": {"home": {"id": self.entity_id, **data}}},
        )

        if (await resp.json()).get("status") == "ok":
            return True

        return False

    async def async_set_persons_home(
        self,
        person_ids: list[str] = None,
    ):
        """Mark persons as home."""
        post_params: dict[str, str | list] = {"home_id": self.entity_id}
        if person_ids:
            post_params["person_ids[]"] = person_ids
        return await self.auth.async_post_request(
            url=_SETPERSONSHOME_REQ,
            params=post_params,
        )

    async def async_set_persons_away(self, person_id: str | None = None):
        """Mark a person as away or set the whole home to being empty."""
        post_params = {"home_id": self.entity_id}
        if person_id:
            post_params["person_id"] = person_id
        return await self.auth.async_post_request(
            url=_SETPERSONSAWAY_REQ,
            params=post_params,
        )


def is_valid_state(data: dict) -> bool:
    """Check set state data."""
    return data is not None
