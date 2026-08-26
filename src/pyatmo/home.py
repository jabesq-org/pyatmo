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
from pyatmo.enums import SCHEDULE_TYPE_MAPPING, TemperatureControlMode
from pyatmo.event import Event
from pyatmo.exceptions import (
    ApiHomeReachabilityError,
    InvalidScheduleError,
    InvalidStateError,
    NoScheduleError,
)
from pyatmo.person import Person
from pyatmo.room import Room
from pyatmo.schedule import Schedule

if TYPE_CHECKING:
    from aiohttp import ClientResponse

    from pyatmo.auth import AbstractAsyncAuth
    from pyatmo.modules import Module
    from pyatmo.modules.netatmo import NACamera

LOG: logging.Logger = logging.getLogger(__name__)

# Legacy/typo module type strings some /homesdata schema variants document,
# mapped to the canonical type the library implements. Defensive: the live API
# is expected to send the canonical spelling.
MODULE_TYPE_ALIASES: dict[str, str] = {
    "NBD": "NDB",  # transposition of Smart Video Doorbell
    "NADoorTag": "NACamDoorTag",  # legacy Smart Door/Window Sensor name
}


class Home:
    """Class to represent a Netatmo home."""

    auth: AbstractAsyncAuth
    entity_id: str
    name: str
    altitude: int | None = None
    coordinates: list[float] | None = None
    country: str | None = None
    timezone: str | None = None
    rooms: dict[str, Room]
    modules: dict[str, Module]
    schedules: dict[str, Schedule]
    persons: dict[str, Person]
    events: dict[str, Event]

    temperature_control_mode: TemperatureControlMode | None = None
    therm_mode: str | None = None
    therm_setpoint_default_duration: int | None = None
    cooling_mode: str | None = None

    def __init__(self, auth: AbstractAsyncAuth, raw_data: RawData) -> None:
        """Initialize a Netatmo home instance."""

        self.auth = auth
        self.entity_id = raw_data["id"]
        self.name = raw_data.get("name", "Unknown")
        self.altitude = raw_data.get("altitude")
        self.coordinates = raw_data.get("coordinates")
        self.country = raw_data.get("country")
        self.timezone = raw_data.get("timezone")
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
        # Room ids seen in /homestatus that the topology never declared. Tracked
        # so each one is reported once instead of on every poll; see Home.update.
        self._unknown_room_ids: set[str] = set()

        self.temperature_control_mode = get_temperature_control_mode(
            raw_data.get("temperature_control_mode"),
        )
        self.therm_mode = raw_data.get("therm_mode")
        self.therm_setpoint_default_duration = raw_data.get(
            "therm_setpoint_default_duration",
        )
        self.cooling_mode = raw_data.get("cooling_mode")

    def get_module(self, module: dict) -> Module:
        """Return module."""

        module_type = MODULE_TYPE_ALIASES.get(module["type"], module["type"])
        if module_type != module["type"]:
            LOG.debug("Aliased device type %s -> %s", module["type"], module_type)
            # Normalize so both the class lookup and DeviceType(...) in
            # Module.__init__ see the canonical type. Copy (not mutate) to avoid
            # rewriting the shared raw_data dict, which consumers may serialize.
            module = {**module, "type": module_type}

        try:
            return getattr(modules, module_type)(
                home=self,
                module=module,
            )
        except AttributeError:
            LOG.info("Unknown device type %s", module_type)
            return modules.NLunknown(
                home=self,
                module=module,
            )

    @property
    def has_status(self) -> bool:
        """Whether `/homestatus` can be called for this home.

        A home carrying no modules has nothing to report: `/homestatus` answers
        `200 {"status": "ok"}` with no `body`, which raises `NoDeviceError` on
        every call, so a caller should not schedule it.

        Device category deliberately plays no part: `/homestatus` does report
        weather modules, so excluding them would hide a home that polls fine.
        """
        return bool(self.modules)

    def update_topology(self, raw_data: RawData) -> None:
        """Update topology."""

        self.name = raw_data.get("name", "Unknown")
        # Geolocation is treated as sticky, unlike the live state below (name,
        # therm mode, ...): it is effectively static per home and only carried
        # in a full /homesdata payload, so a topology update that omits these
        # keys keeps the previously populated values instead of wiping them.
        self.altitude = raw_data.get("altitude", self.altitude)
        self.coordinates = raw_data.get("coordinates", self.coordinates)
        self.country = raw_data.get("country", self.country)
        self.timezone = raw_data.get("timezone", self.timezone)

        raw_modules = raw_data.get("modules", [])

        self.temperature_control_mode = get_temperature_control_mode(
            raw_data.get("temperature_control_mode"),
        )
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

        raw_schedules = raw_data.get("schedules", [])
        for schedule in raw_schedules:
            if (schedule_id := schedule["id"]) not in self.schedules:
                self.schedules[schedule_id] = Schedule(home=self, raw_data=schedule)
            else:
                self.schedules[schedule_id].update_topology(schedule)

        # Drop schedule if has been removed
        for schedule in self.schedules.keys() - {s["id"] for s in raw_schedules}:
            self.schedules.pop(schedule)

    async def update(
        self,
        raw_data: RawData,
        do_raise_for_reachability_error: bool = False,
    ) -> None:
        """Update home with the latest data."""
        has_error = False
        for module in raw_data.get("errors", []):
            has_error = True
            module_id = module["id"]
            if module_id in self.modules:
                # Mark BEFORE update({}): reflection now preserves the value, so
                # the False survives and still drives the bridged-children and
                # room cascade inside Module.update.
                self.modules[module_id].mark_unreachable()
                await self.modules[module_id].update({})
                # Set error_code AFTER update({}): update() reruns reflection
                # (_update_attributes) which would otherwise reset it to None.
                self.modules[module_id].error_code = module.get("code")
            else:
                LOG.warning(
                    "Error reported for unknown module id (%s); skipping",
                    module_id,
                )

        data = raw_data["home"]

        has_an_update = False
        for module in data.get("modules", []):
            has_an_update = True
            if module["id"] not in self.modules:
                # Register the newly-seen module directly. Routing through
                # update_topology with a partial `{"modules": [...]}` payload
                # would wipe home-level fields (name, therm state, geolocation)
                # whose keys are absent from this /homestatus data.
                self.modules[module["id"]] = self.get_module(module)
            if self.modules[module["id"]].error_code is not None:
                # Reported healthy again after an errors[] entry. Drop the mark
                # BEFORE update(), because reflection passes the attribute's current
                # value as its fallback -- clearing afterwards would leave the stale
                # False in place for exactly the poll that reports recovery.
                #
                # The error_code condition is an optimisation, not a correctness
                # guard: clearing unconditionally gives the same results but walks
                # every bridge's children on every poll.
                self.modules[module["id"]].clear_unreachable()
            await self.modules[module["id"]].update(module)
            # Clear any error code from a previous /homestatus errors[] entry:
            # the module is reported healthy again. Reflection in update() would
            # otherwise carry the stale code forward (raw data has no error_code).
            self.modules[module["id"]].error_code = None

        for room in data.get("rooms", []):
            has_an_update = True
            room_id = room["id"]
            if room_id in self.rooms:
                self.rooms[room_id].update(room)
                # Re-arm the warning: the topology declares this room again, so
                # should it drop out later that is fresh news worth reporting.
                self._unknown_room_ids.discard(room_id)
            elif room_id not in self._unknown_room_ids:
                # Some homes (seen on Legrand/Bubendorff) carry a room in
                # /homestatus that /homesdata never declares, on every poll
                # forever. The room is skipped either way -- building one needs
                # the name and type only the topology carries -- but the
                # condition is not user-fixable, so report it once per id
                # instead of once per poll.
                self._unknown_room_ids.add(room_id)
                LOG.warning(
                    "Room id (%s) not found in known rooms. Known room ids: %s (count=%d)",
                    room_id,
                    list(self.rooms.keys()),
                    len(self.rooms),
                )
            else:
                LOG.debug("Room id (%s) still not found in known rooms", room_id)

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

    def set_selected_schedule(self, schedule_id: str) -> None:
        """Mark the given schedule as selected locally, without any API call."""
        if not self.is_valid_schedule(schedule_id):
            msg: str = f"{schedule_id} is not a valid schedule id"
            raise NoScheduleError(msg)

        schedule_type = self.schedules[schedule_id].type
        for sid, schedule in self.schedules.items():
            if schedule.type == schedule_type:
                schedule.selected = sid == schedule_id

    def get_available_schedules(self) -> list[Schedule]:
        """Return available schedules for given home."""

        return [
            schedule
            for schedule in self.schedules.values()
            if self.temperature_control_mode
            and schedule.type == SCHEDULE_TYPE_MAPPING[self.temperature_control_mode]
        ]

    def get_schedule_by_name(self, name: str) -> Schedule | None:
        """Return the selectable schedule with the given name, if any."""

        return next(
            (
                schedule
                for schedule in self.get_available_schedules()
                if schedule.name == name
            ),
            None,
        )

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
        mode: str | None,
        end_time: int | None = None,
        schedule_id: str | None = None,
    ) -> bool:
        """Set thermotat mode."""
        if schedule_id is not None and not self.is_valid_schedule(schedule_id):
            msg = f"{schedule_id} is not a valid schedule id."
            raise NoScheduleError(msg)
        if mode is None:
            msg = f"{mode} is not a valid mode."
            raise NoScheduleError(msg)

        post_params: dict[str, str] = {"home_id": self.entity_id, "mode": mode}
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

        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=SETTHERMMODE_ENDPOINT,
            params=post_params,
        )

        return (await resp.json()).get("status") == "ok"

    async def async_switch_schedule(self, schedule_id: str) -> bool:
        """Switch the schedule."""
        if not self.is_valid_schedule(schedule_id):
            msg: str = f"{schedule_id} is not a valid schedule id"
            raise NoScheduleError(msg)
        LOG.debug("Setting home (%s) schedule to %s", self.entity_id, schedule_id)
        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=SWITCHHOMESCHEDULE_ENDPOINT,
            params={"home_id": self.entity_id, "schedule_id": schedule_id},
        )

        if (await resp.json()).get("status") != "ok":
            return False

        self.set_selected_schedule(schedule_id)

        return True

    async def async_set_state(self, data: dict[str, Any]) -> bool:
        """Set state using given data."""
        if not is_valid_state(data):
            msg = "Data for '/set_state' contains errors."
            raise InvalidStateError(msg)
        LOG.debug("Setting state for home (%s) according to %s", self.entity_id, data)
        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=SETSTATE_ENDPOINT,
            params={"json": {"home": {"id": self.entity_id, **data}}},
        )

        response = await resp.json()
        body = response.get("body")
        if isinstance(body, dict) and (errors := body.get("errors")):
            LOG.warning(
                "Set state response for home %s contains errors: status=%r errors=%r",
                self.entity_id,
                response.get("status"),
                errors,
            )
            return False
        return response.get("status") == "ok"

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

        post_params: dict[str, str] = {"home_id": self.entity_id}
        if person_id:
            post_params["person_id"] = person_id
        return await self.auth.async_post_api_request(
            endpoint=SETPERSONSAWAY_ENDPOINT,
            params=post_params,
        )

    async def async_set_schedule_temperatures(
        self,
        zone_id: str,
        temps: dict[str, float],
    ) -> None:
        """Set the scheduled room temperature for the given schedule ID."""

        selected_schedule: Schedule | None = self.get_selected_schedule()

        if selected_schedule is None:
            msg = "Could not determine selected schedule."
            raise NoScheduleError(msg)

        for zone in (z for z in selected_schedule.zones if z.entity_id == zone_id):
            for room in (r for r in zone.rooms if r.entity_id in temps):
                room.therm_setpoint_temperature = temps[room.entity_id]

        await self.async_sync_schedule(selected_schedule)

    async def async_sync_schedule(
        self,
        schedule: Schedule,
    ) -> None:
        """Modify an existing schedule."""
        if not is_valid_schedule(schedule):
            msg = "Data for '/synchomeschedule' contains errors."
            raise InvalidScheduleError(msg)
        LOG.debug(
            "Setting schedule (%s) for home (%s) to %s",
            schedule.entity_id,
            self.entity_id,
            schedule,
        )

        timetable_entries: list[dict[str, int | None]] = [
            {
                "m_offset": timetable_entry.m_offset,
                "zone_id": timetable_entry.zone_id,
            }
            for timetable_entry in schedule.timetable
        ]

        zones: list[dict[str, Any]] = []
        for zone in schedule.zones:
            new_zone: dict[str, Any] = {
                "id": zone.entity_id,
                "name": zone.name,
                "type": zone.type,
                "rooms": [
                    {
                        "id": room.entity_id,
                        "therm_setpoint_temperature": room.therm_setpoint_temperature,
                    }
                    for room in zone.rooms
                ],
            }
            zones.append(new_zone)

        request_json: dict[str, Any] = {
            "away_temp": schedule.away_temp,
            "hg_temp": schedule.hg_temp,
            "timetable": timetable_entries,
            "zones": zones,
        }

        resp: ClientResponse = await self.auth.async_post_api_request(
            endpoint=SYNCHOMESCHEDULE_ENDPOINT,
            params={
                "params": {
                    "home_id": self.entity_id,
                    "schedule_id": schedule.entity_id,
                    "name": "Default",
                },
                "json": request_json,
            },
        )

        return (await resp.json()).get("status") == "ok"


def is_valid_state(data: dict[str, Any]) -> bool:
    """Check set state data."""
    return data is not None


def is_valid_schedule(schedule: Schedule) -> bool:
    """Check schedule."""
    return (
        isinstance(schedule, Schedule)
        and hasattr(schedule, "entity_id")
        and schedule.entity_id != ""
    )


def get_temperature_control_mode(
    temperature_control_mode: str | None,
) -> TemperatureControlMode | None:
    """Return temperature control mode.

    Unknown values degrade to None with a warning rather than raising, so a
    single unrecognized mode never aborts topology parsing for the whole
    account.
    """
    if not temperature_control_mode:
        return None
    try:
        return TemperatureControlMode(temperature_control_mode)
    except ValueError:
        LOG.warning(
            "%s temperature control mode is unknown",
            temperature_control_mode,
        )
        return None
