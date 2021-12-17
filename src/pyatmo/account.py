"""Support for a Netatmo account."""
from __future__ import annotations

import logging
from abc import ABC
from typing import Callable

from pyatmo.auth import AbstractAsyncAuth
from pyatmo.const import (
    _GETHOMESDATA_REQ,
    _GETHOMESTATUS_REQ,
    _SETROOMTHERMPOINT_REQ,
    _SETTHERMMODE_REQ,
    _SWITCHHOMESCHEDULE_REQ,
)
from pyatmo.exceptions import NoSchedule
from pyatmo.helpers import extract_raw_data_new
from pyatmo.home import NetatmoHome

LOG = logging.getLogger(__name__)


class AbstractAccount(ABC):
    """Abstract class of a Netatmo account."""

    user: str | None = None
    home_ids: list[str] = []
    homes: dict[str, NetatmoHome] = {}
    subscriptions: dict[str, Callable] = {}
    raw_data: dict = {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(user={self.user}, home_ids={self.home_ids}, subscriptions={self.subscriptions})"
        )

    # def register_handler(self, home_id: str, handler: Callable) -> None:
    #     """Register update handler."""
    #     if self.subscriptions.get(home_id) == handler:
    #         return

    #     if home_id in self.subscriptions and self.subscriptions[home_id] != handler:
    #         self.unregister_handler(home_id)

    #     self.subscriptions[home_id] = handler

    #     self.publish()

    # def unregister_handler(self, home_id: str) -> None:
    #     """Unregister update handler."""
    #     self.subscriptions.pop(home_id)

    # def publish(self) -> None:
    #     """Publish latest topology data to subscribers."""
    #     for home in self.raw_data.get("homes", []):
    #         if (home_id := home["id"]) in self.subscriptions:
    #             self.subscriptions[home_id](home)

    def process_topology(self) -> None:
        """Process topology information from /homedata."""
        for home in self.raw_data["homes"]:
            if (home_id := home["id"]) in self.homes:
                self.homes[home_id].update_topology(home)
            else:
                self.homes[home_id] = NetatmoHome(raw_data=home)


class AsyncAccount(AbstractAccount):
    """Async class of a Netatmo account."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo account.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth

    async def async_update_topology(self) -> None:
        """Retrieve topology data from /homesdata."""
        resp = await self.auth.async_post_request(url=_GETHOMESDATA_REQ)
        self.raw_data = extract_raw_data_new(await resp.json(), "homes")

        self.user = self.raw_data.get("user", {}).get("email")

        self.process_topology()

    async def async_update_status(self, home_id: str) -> None:
        """Retrieve topology data from /homestatus."""
        resp = await self.auth.async_post_request(
            url=_GETHOMESTATUS_REQ,
            params={"home_id": home_id},
        )
        raw_data = extract_raw_data_new(await resp.json(), "home")
        self.homes[home_id].update(raw_data)

    async def async_set_room_thermpoint(
        self,
        home_id: str,
        room_id: str,
        mode: str,
        temp: float = None,
        end_time: int = None,
    ) -> str | None:
        """Set room temperature set point."""
        post_params = {
            "home_id": home_id,
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
        home_id: str,
        mode: str,
        end_time: int = None,
        schedule_id: str = None,
    ) -> str | None:
        """Set thermotat mode."""
        if schedule_id is not None and not self.homes[home_id].is_valid_schedule(
            schedule_id,
        ):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id.")

        if mode is None:
            raise NoSchedule(f"{mode} is not a valid mode.")

        post_params = {"home_id": home_id, "mode": mode}
        if end_time is not None and mode in {"hg", "away"}:
            post_params["endtime"] = str(end_time)

        if schedule_id is not None and mode == "schedule":
            post_params["schedule_id"] = schedule_id

        LOG.debug("Setting home (%s) mode to %s (%s)", home_id, mode, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SETTHERMMODE_REQ,
            params=post_params,
        )
        assert not isinstance(resp, bytes)
        return await resp.json()

    async def async_switch_home_schedule(self, home_id: str, schedule_id: str) -> None:
        """Switch the schedule for a give home ID."""
        if not self.homes[home_id].is_valid_schedule(schedule_id):
            raise NoSchedule(f"{schedule_id} is not a valid schedule id")

        LOG.debug("Setting home (%s) schedule to %s", home_id, schedule_id)
        resp = await self.auth.async_post_request(
            url=_SWITCHHOMESCHEDULE_REQ,
            params={"home_id": home_id, "schedule_id": schedule_id},
        )
        LOG.debug("Response: %s", resp)
