"""Module to represent a Netatmo home."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse

from pyatmo import modules
from pyatmo.const import (
    ENERGY_ELEC_OFF_IDX,
    ENERGY_ELEC_PEAK_IDX,
    EVENTS,
    SCHEDULE_TYPE_ELECTRICITY,
    SCHEDULE_TYPE_THERM,
    SCHEDULES,
    SETPERSONSAWAY_ENDPOINT,
    SETPERSONSHOME_ENDPOINT,
    SETSTATE_ENDPOINT,
    SETTHERMMODE_ENDPOINT,
    SWITCHHOMESCHEDULE_ENDPOINT,
    SYNCHOMESCHEDULE_ENDPOINT,
    MeasureType,
    RawData,
)
from pyatmo.event import Event
from pyatmo.exceptions import InvalidSchedule, InvalidState, NoSchedule
from pyatmo.modules import Module
from pyatmo.person import Person
from pyatmo.room import Room
from pyatmo.schedule import Schedule, ThermSchedule, schedule_factory

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


class Home:
    """Class to represent a Netatmo home."""

    auth: AbstractAsyncAuth
    entity_id: str
    name: str
    rooms: dict[str, Room]
    modules: dict[str, Module]
    schedules: dict[str, Schedule]  # for compatibility should diseappear
    all_schedules: dict[dict[str, str, Schedule]] | {}
    persons: dict[str, Person]
    events: dict[str, Event]
    energy_endpoints: list[str]
    energy_schedule: list[int]

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
        self._handle_schedules(raw_data.get(SCHEDULES, []))
        self.persons = {
            s["id"]: Person(home=self, raw_data=s) for s in raw_data.get("persons", [])
        }
        self.events = {}

    def _handle_schedules(self, raw_data):

        schedules = {}

        self.schedules = {}

        for s in raw_data:
            # strange but Energy plan are stored in schedules, we should handle this one differently
            sched, schedule_type = schedule_factory(home=self, raw_data=s)
            if schedule_type not in schedules:
                schedules[schedule_type] = {}
            schedules[schedule_type][s["id"]] = sched
            self.schedules[s["id"]] = sched

        self.all_schedules = schedules

        nrj_schedule = next(
            iter(schedules.get(SCHEDULE_TYPE_ELECTRICITY, {}).values()), None
        )

        self.energy_schedule_vals = []
        self.energy_endpoints = [MeasureType.SUM_ENERGY_ELEC_BASIC.value]
        if nrj_schedule is not None:

            # Tariff option (basic = always the same price, peak_and_off_peak = peak & off peak hours)
            type_tariff = nrj_schedule.tariff_option
            zones = nrj_schedule.zones

            if type_tariff == "peak_and_off_peak" and len(zones) >= 2:

                self.energy_endpoints = [None, None]

                self.energy_endpoints[ENERGY_ELEC_PEAK_IDX] = (
                    MeasureType.SUM_ENERGY_ELEC_PEAK.value
                )
                self.energy_endpoints[ENERGY_ELEC_OFF_IDX] = (
                    MeasureType.SUM_ENERGY_ELEC_OFF_PEAK.value
                )

                if zones[0].price_type == "peak":
                    peak_id = zones[0].entity_id
                else:
                    peak_id = zones[1].entity_id

                timetable = nrj_schedule.timetable

                # timetable are daily for electricity type, and sorted from begining to end
                for t in timetable:

                    time = (
                        t.m_offset * 60
                    )  # m_offset is in minute from the begininng of the day
                    if len(self.energy_schedule_vals) == 0:
                        time = 0

                    pos_to_add = ENERGY_ELEC_OFF_IDX
                    if t.zone_id == peak_id:
                        pos_to_add = ENERGY_ELEC_PEAK_IDX

                    self.energy_schedule_vals.append((time, pos_to_add))

            else:
                self.energy_endpoints = [MeasureType.SUM_ENERGY_ELEC_BASIC.value]

    def get_module(self, module: dict) -> Module:
        """Return module."""

        try:
            return getattr(modules, module["type"])(
                home=self,
                module=module,
            )
        except AttributeError:
            LOG.info("Unknown device type %s", module["type"])
            return getattr(modules, "NLunknown")(
                home=self,
                module=module,
            )

    def update_topology(self, raw_data: RawData) -> None:
        """Update topology."""

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

        self._handle_schedules(raw_data.get(SCHEDULES, []))

    async def update(self, raw_data: RawData) -> bool:
        """Update home with the latest data."""
        num_errors = 0
        for module in raw_data.get("errors", []):
            num_errors += 1
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
                setattr(
                    module,
                    "events",
                    [
                        event
                        for event in self.events.values()
                        if getattr(event, "module_id") == module.entity_id
                    ],
                )

        if (
            num_errors > 0
            and has_one_module_reachable is False
            and has_an_update is False
        ):
            return False

        return True

    def get_selected_schedule(self, schedule_type: str = None) -> Schedule | None:
        """Return selected schedule for given home."""
        if schedule_type is None:
            schedule_type = SCHEDULE_TYPE_THERM

        schedules = self.all_schedules.get(schedule_type, {})

        return next(
            (schedule for schedule in schedules.values() if schedule.selected),
            None,
        )

    def get_selected_temperature_schedule(self) -> ThermSchedule | None:
        """Return selected temperature schedule for given home."""

        return self.get_selected_schedule(schedule_type=SCHEDULE_TYPE_THERM)

    def is_valid_schedule(self, schedule_id: str) -> bool:
        """Check if valid schedule."""
        for schedules in self.all_schedules.values():
            if schedule_id in schedules:
                return True

        return False

    def has_otm(self) -> bool:
        """Check if any room has an OTM device."""

        return any("OTM" in room.device_types for room in self.rooms.values())

    def get_hg_temp(self) -> float | None:
        """Return frost guard temperature value for given home."""

        if (schedule := self.get_selected_temperature_schedule()) is None:
            return None
        return schedule.hg_temp

    def get_away_temp(self) -> float | None:
        """Return configured away temperature value for given home."""

        if (schedule := self.get_selected_temperature_schedule()) is None:
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

    async def async_set_schedule_temperatures(
        self,
        zone_id: int,
        temps: dict[str, int],
    ) -> None:
        """Set the scheduled room temperature for the given schedule ID."""

        selected_schedule = self.get_selected_temperature_schedule()

        if selected_schedule is None:
            raise NoSchedule("Could not determine selected schedule.")

        zones = []

        timetable_entries = [
            {
                "m_offset": timetable_entry.m_offset,
                "zone_id": timetable_entry.zone_id,
            }
            for timetable_entry in selected_schedule.timetable
        ]

        for zone in selected_schedule.zones:
            new_zone = {
                "id": zone.entity_id,
                "name": zone.name,
                "type": zone.type,
                "rooms": [],
            }

            for room in zone.rooms:
                temp = room.therm_setpoint_temperature
                if zone.entity_id == zone_id and room.entity_id in temps:
                    temp = temps[room.entity_id]

                new_zone["rooms"].append(
                    {"id": room.entity_id, "therm_setpoint_temperature": temp},
                )

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
            raise InvalidSchedule("Data for '/synchomeschedule' contains errors.")
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
