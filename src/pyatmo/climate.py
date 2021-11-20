"""Support for Netatmo energy devices (relays, thermostats and valves)."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

import logging
from abc import ABC

from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .const import (
    _GETHOMESTATUS_REQ,
    _SETROOMTHERMPOINT_REQ,
    _SETTHERMMODE_REQ,
    _SWITCHHOMESCHEDULE_REQ,
)
from .exceptions import NoSchedule
from .helpers import extract_raw_data_new
from .home import NetatmoHome

LOG = logging.getLogger(__name__)


class AbstractClimate(ABC):
    """Abstract class of Netatmo energy devices."""

    home_id: str
    homes: dict = {}
    modules: dict = {}
    rooms: dict = {}
    schedules: dict = {}

    raw_data: dict | None = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(home_id={self.home_id})"

    def process(self, raw_data: dict) -> None:
        """Process raw status data from the energy endpoint."""
        if self.home_id != raw_data["home"].get("id"):
            LOG.debug(
                "Home id '%s' does not match. '%s'",
                raw_data["home"].get("id"),
                {self.home_id},
            )
            return

        if self.home_id not in self.homes:
            self.raw_data = raw_data
            return

        self.homes[self.home_id].update(raw_data)
        self.raw_data = None

    def process_topology(self, raw_data: dict) -> None:
        """Process topology information from /homedata."""
        if self.home_id not in self.homes:
            self.homes[self.home_id] = NetatmoHome(raw_data=raw_data)
        else:
            self.homes[self.home_id].update_topology(raw_data)

        if self.raw_data:
            self.process(self.raw_data)


class AsyncClimate(AbstractClimate):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: AbstractAsyncAuth, home_id: str) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth
        self.home_id = home_id

    async def async_update(self) -> None:
        """Fetch and process data from API."""
        resp = await self.auth.async_post_request(
            url=_GETHOMESTATUS_REQ,
            params={"home_id": self.home_id},
        )
        raw_data = extract_raw_data_new(await resp.json(), "home")
        self.process(raw_data)

    async def async_set_room_thermpoint(
        self,
        room_id: str,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> str | None:
        """Set room temperature set point."""
        post_params = {
            "home_id": self.home_id,
            "room_id": room_id,
            "mode": mode,
        }
        # Temp and endtime should only be send when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            post_params["temp"] = str(temp)

        if end_time is not None:
            post_params["endtime"] = str(end_time)

        LOG.debug(
            "Setting room (%s) temperature set point to %s until %s",
            room_id,
            temp,
            end_time,
        )
        resp = await self.auth.async_post_request(
            url=_SETROOMTHERMPOINT_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_set_thermmode(
        self,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> str | None:
        """Set thermotat mode."""
        if schedule_id is not None and not self.homes[self.home_id].is_valid_schedule(
            schedule_id,
        ):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id.")

        if mode is None:
            raise NoSchedule(f"{mode} is not a valid mode.")

        post_params = {"home_id": self.home_id, "mode": mode}
        if end_time is not None and mode in {"hg", "away"}:
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        LOG.debug("Setting home (%s) mode to %s (%s)", self.home_id, mode, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SETTHERMMODE_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_switch_home_schedule(self, schedule_id: str) -> None:
        """Switch the schedule for a give home ID."""
        if not self.homes[self.home_id].is_valid_schedule(schedule_id):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id")

        LOG.debug("Setting home (%s) schedule to %s", self.home_id, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SWITCHHOMESCHEDULE_REQ,
            params={"home_id": self.home_id, "schedule_id": schedule_id},
        )
        LOG.debug("Response: %s", resp)


class Climate(AbstractClimate):
    """Class of Netatmo energy devices."""

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize the Netatmo home data.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
        """
        self.auth = auth

    def update(self) -> None:
        """Fetch and process data from API."""
        if not self.homes:
            LOG.debug('Topology for home "{self.home_id}" has not been initialized.')
            return

        resp = self.auth.post_request(url=_GETHOMESTATUS_REQ)

        raw_data = extract_raw_data_new(resp.json(), "home")
        self.process(raw_data)
