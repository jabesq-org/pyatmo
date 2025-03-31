"""Module to represent a Netatmo home."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from pyatmo import modules
from pyatmo.const import (
    EVENTS,
    SCHEDULES,
    SETPERSONSAWAY_ENDPOINT,
    SETPERSONSHOME_ENDPOINT,
    SETSTATE_ENDPOINT,
    SETTHERMMODE_ENDPOINT,
    SWITCHHOMESCHEDULE_ENDPOINT,
    SYNCHOMESCHEDULE_ENDPOINT,
    RawData,
)
from pyatmo.event import Event
from pyatmo.exceptions import (
    ApiHomeReachabilityError,
    InvalidSchedule,
    InvalidState,
    NoSchedule,
)
from pyatmo.person import Person
from pyatmo.room import Room
from pyatmo.schedule import Schedule, ScheduleType

if TYPE_CHECKING:
    from aiohttp import ClientResponse

    from pyatmo.auth import AbstractAsyncAuth
    from pyatmo.modules import Module
    from pyatmo.modules.netatmo import NACamera

LOG = logging.getLogger(__name__)


SCHEDULE_TYPE_MAPPING = {
    "heating": ScheduleType.THERM,
    "cooling": ScheduleType.COOLING,
}


class Home:
    """Class to represent a Netatmo home."""

    auth: AbstractAsyncAuth
    entity_id: str
    name: str
    rooms: dict[str, Room]
    modules: dict[str, Module]
    schedules: dict[str, Schedule]
    persons: dict[str, Person]
    events: dict[str, Event]

    temperature_control_mode: str | None = None
    therm_mode: str | None = None
    therm_setpoint_default_duration: int | None = None
    cooling_mode: str | None = None

    def __init__(self, auth: AbstractAsyncAuth, raw_data: RawData) -> None:
        """Initialize a Netatmo home instance."""

        self.auth = auth
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", "Unknown")
        self.modules = {
            module["id"]: self.get_module(module)
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

        self.temperature_control_mode = raw_data.get("temperature_control_mode")
        self.therm_mode = raw_data.get("therm_mode")
        self.therm_setpoint_default_duration = raw_data.get(
            "therm_setpoint_default_duration",
        )
        self.cooling_mode = raw_data.get("cooling_mode")

    def get_module(self, module: dict) -> Module:
        """Return module."""

        try:
            return getattr(modules, module["type"])(
                home=self,
                module=module,
            )
        except AttributeError:
            LOG.info("Unknown device type %s", module["type"])
            return modules.NLunknown(
                home=self,
                module=module,
            )

    def update_topology(self, raw_data: RawData) -> None:
        """Update topology."""

        self.name = raw_data.get("name", "Unknown")

        raw_modules = raw_data.get("modules", [])

        self.temperature_control_mode = raw_data.get("temperature_control_mode")
        self.therm_mode = raw_data.get("therm_mode")
        self.therm_setpoint_default_duration = raw_data.get(
            "therm_setpoint_default_duration",
        )
        self.cooling_mode = raw_data.get("cooling_mode")

        for module in raw_modules:
            if (module_id := module["id"]) not in self.modules:
                self.modules[module_id] = self.get_module(module)
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

    async def update(
        self,
        raw_data: RawData,
        do_raise_for_reachability_error: bool = False,
    ) -> None:
        """Update home with the latest data."""
        has_error = False
        for module in raw_data.get("errors", []):
            has_error = True
            await self.modules[module["id"]].update({})

        data = raw_data["home"]

        has_an_update = False
        for module in data.get("modules", []):
            has_an_update = True
            if module["id"] not in self.modules:
                self.update_topology({"modules": [module]})
            await self.modules[module["id"]].update(module)

        for room in data.get("rooms", []):
            has_an_update = True
            self.rooms[room["id"]].update(room)

        for person_status in data.get("persons", []):
            # if there is a person update, it means the house has been updated
            has_an_update = True
            if person := self.persons.get(person_status["id"]):
                person.update(person_status)

        self.events = {
            s["id"]: Event(home_id=self.entity_id, raw_data=s)
            for s in data.get(EVENTS, [])
        }
        if len(self.events) > 0:
            has_an_update = True

        has_one_module_reachable = False
        for module in self.modules.values():
            if module.reachable:
                has_one_module_reachable = True
            if hasattr(module, "events"):
                module = cast("NACamera", module)
                module.events = [
                    event
                    for event in self.events.values()
                    if event.module_id == module.entity_id
                ]

        if (
            do_raise_for_reachability_error
            and has_error
            and has_one_module_reachable is False
            and has_an_update is False
        ):
            msg = "No Home update could be performed, all modules unreachable and not updated"
            raise ApiHomeReachabilityError(
                msg,
            )

    def get_selected_schedule(self) -> Schedule | None:
        """Return selected schedule for given home."""

        return next(
            (
                schedule
                for schedule in self.schedules.values()
                if schedule.selected
                and self.temperature_control_mode
                and schedule.type
                == SCHEDULE_TYPE_MAPPING[self.temperature_control_mode]
            ),
            None,
        )

    def get_available_schedules(self) -> list[Schedule]:
        """Return available schedules for given home."""

        return [
            schedule
            for schedule in self.schedules.values()
            if self.temperature_control_mode
            and schedule.type == SCHEDULE_TYPE_MAPPING[self.temperature_control_mode]
        ]

    def is_valid_schedule(self, schedule_id: str) -> bool:
        """Check if valid schedule."""

        return schedule_id in self.schedules

    def has_otm(self) -> bool:
        """Check if any room has an OTM device."""

        return any("OTM" in room.device_types for room in self.rooms.values())

    def has_bns(self) -> bool:
        """Check if any room has a BNS device."""

        return any("BNS" in room.device_types for room in self.rooms.values())

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
            msg = f"{schedule_id} is not a valid schedule id."
            raise NoSchedule(msg)
        if mode is None:
            msg = f"{mode} is not a valid mode."
            raise NoSchedule(msg)
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
            msg = f"{schedule_id} is not a valid schedule id"
            raise NoSchedule(msg)
        LOG.debug("Setting home (%s) schedule to %s", self.entity_id, schedule_id)
        resp = await self.auth.async_post_api_request(
            endpoint=SWITCHHOMESCHEDULE_ENDPOINT,
            params={"home_id": self.entity_id, "schedule_id": schedule_id},
        )

        return (await resp.json()).get("status") == "ok"

    async def async_set_state(self, data: dict[str, Any]) -> bool:
        """Set state using given data."""
        if not is_valid_state(data):
            msg = "Data for '/set_state' contains errors."
            raise InvalidState(msg)
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

    async def async_set_schedule_temperatures(
        self,
        zone_id: int,
        temps: dict[str, int],
    ) -> None:
        """Set the scheduled room temperature for the given schedule ID."""

        selected_schedule = self.get_selected_schedule()

        if selected_schedule is None:
            msg = "Could not determine selected schedule."
            raise NoSchedule(msg)

        zones = []

        timetable_entries = [
            {
                "m_offset": timetable_entry.m_offset,
                "zone_id": timetable_entry.zone_id,
            }
            for timetable_entry in selected_schedule.timetable
        ]

        for zone in selected_schedule.zones:
            rooms = []
            new_zone = {
                "id": zone.entity_id,
                "name": zone.name,
                "type": zone.type,
            }

            for room in zone.rooms:
                temp = room.therm_setpoint_temperature
                if zone.entity_id == zone_id and room.entity_id in temps:
                    temp = temps[room.entity_id]

                rooms.append(
                    {"id": room.entity_id, "therm_setpoint_temperature": temp},
                )

            new_zone["rooms"] = rooms
            zones.append(new_zone)

        schedule = {
            "away_temp": selected_schedule.away_temp,
            "hg_temp": selected_schedule.hg_temp,
            "timetable": timetable_entries,
            "zones": zones,
        }

        await self.async_sync_schedule(selected_schedule.entity_id, schedule)

    async def async_sync_schedule(
        self,
        schedule_id: str,
        schedule: dict[str, Any],
    ) -> None:
        """Modify an existing schedule."""
        if not is_valid_schedule(schedule):
            msg = "Data for '/synchomeschedule' contains errors."
            raise InvalidSchedule(msg)
        LOG.debug(
            "Setting schedule (%s) for home (%s) to %s",
            schedule_id,
            self.entity_id,
            schedule,
        )

        resp = await self.auth.async_post_api_request(
            endpoint=SYNCHOMESCHEDULE_ENDPOINT,
            params={
                "params": {
                    "home_id": self.entity_id,
                    "schedule_id": schedule_id,
                    "name": "Default",
                },
                "json": schedule,
            },
        )

        return (await resp.json()).get("status") == "ok"


def is_valid_state(data: dict[str, Any]) -> bool:
    """Check set state data."""
    return data is not None


def is_valid_schedule(schedule: dict[str, Any]) -> bool:
    """Check schedule."""
    return schedule is not None
