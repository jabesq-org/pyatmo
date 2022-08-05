"""Module to represent a Netatmo home."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse

from pyatmo import modules
from pyatmo.const import (
    EVENTS,
    SCHEDULES,
    SETPERSONSAWAY_ENDPOINT,
    SETPERSONSHOME_ENDPOINT,
    SETSTATE_ENDPOINT,
    SETTHERMMODE_ENDPOINT,
    SWITCHHOMESCHEDULE_ENDPOINT,
    RawData,
)
from pyatmo.event import Event
from pyatmo.exceptions import InvalidState, NoSchedule
from pyatmo.person import Person
from pyatmo.room import Room
from pyatmo.schedule import Schedule

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


class Home:
    """Class to represent a Netatmo home."""

    auth: AbstractAsyncAuth
    entity_id: str
    name: str
    rooms: dict[str, Room]
    modules: dict[str, modules.Module]
    schedules: dict[str, Schedule]
    persons: dict[str, Person]
    events: dict[str, Event]

    def __init__(self, auth: AbstractAsyncAuth, raw_data: RawData) -> None:
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
            room["id"]: Room(
                home=self,
                room=room,
                all_modules=self.modules,
            )
            for room in raw_data.get("rooms", [])
        }
        self.schedules = {
            s["id"]: Schedule(home=self, raw_data=s)
            for s in raw_data.get(SCHEDULES, [])
        }
        self.persons = {
            s["id"]: Person(home=self, raw_data=s) for s in raw_data.get("persons", [])
        }
        self.events = {}

    def update_topology(self, raw_data: RawData) -> None:
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
                self.rooms[room_id] = Room(
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
            s["id"]: Schedule(home=self, raw_data=s)
            for s in raw_data.get(SCHEDULES, [])
        }

    async def update(self, raw_data: RawData) -> None:
        for module in raw_data.get("errors", []):
            await self.modules[module["id"]].update({})

        data = raw_data["home"]

        for module in data.get("modules", []):
            await self.modules[module["id"]].update(module)

        for room in data.get("rooms", []):
            self.rooms[room["id"]].update(room)

        self.events = {
            s["id"]: Event(home_id=self.entity_id, raw_data=s)
            for s in data.get(EVENTS, [])
        }
        for module in self.modules.values():
            if hasattr(module, "events"):
                setattr(
                    module,
                    "events",
                    [
                        event
                        for event in self.events.values()
                        if getattr(event, "module_id") == module.entity_id
                    ],
                )

    def get_selected_schedule(self) -> Schedule | None:
        """Return selected schedule for given home."""
        return next(
            (schedule for schedule in self.schedules.values() if schedule.selected),
            None,
        )

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
        end_time: int | None = None,
        schedule_id: str | None = None,
    ) -> bool:
        """Set thermotat mode."""
        if schedule_id is not None and not self.is_valid_schedule(schedule_id):
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

        resp = await self.auth.async_post_api_request(
            endpoint=SETTHERMMODE_ENDPOINT,
            params=post_params,
        )

        return (await resp.json()).get("status") == "ok"

    async def async_switch_schedule(self, schedule_id: str) -> bool:
        """Switch the schedule."""
        if not self.is_valid_schedule(schedule_id):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id")
        LOG.debug("Setting home (%s) schedule to %s", self.entity_id, schedule_id)
        resp = await self.auth.async_post_api_request(
            endpoint=SWITCHHOMESCHEDULE_ENDPOINT,
            params={"home_id": self.entity_id, "schedule_id": schedule_id},
        )

        return (await resp.json()).get("status") == "ok"

    async def async_set_state(self, data: dict[str, Any]) -> bool:
        """Set state using given data."""
        if not is_valid_state(data):
            raise InvalidState("Data for '/set_state' contains errors.")
        LOG.debug("Setting state for home (%s) according to %s", self.entity_id, data)
        resp = await self.auth.async_post_api_request(
            endpoint=SETSTATE_ENDPOINT,
            params={"json": {"home": {"id": self.entity_id, **data}}},
        )

        return (await resp.json()).get("status") == "ok"

    async def async_set_persons_home(
        self,
        person_ids: list[str] | None = None,
    ) -> ClientResponse:
        """Mark persons as home."""
        post_params: dict[str, Any] = {"home_id": self.entity_id}
        if person_ids:
            post_params["person_ids[]"] = person_ids
        return await self.auth.async_post_api_request(
            endpoint=SETPERSONSHOME_ENDPOINT,
            params=post_params,
        )

    async def async_set_persons_away(
        self,
        person_id: str | None = None,
    ) -> ClientResponse:
        """Mark a person as away or set the whole home to being empty."""
        post_params = {"home_id": self.entity_id}
        if person_id:
            post_params["person_id"] = person_id
        return await self.auth.async_post_api_request(
            endpoint=SETPERSONSAWAY_ENDPOINT,
            params=post_params,
        )


def is_valid_state(data: dict[str, Any]) -> bool:
    """Check set state data."""
    return data is not None
