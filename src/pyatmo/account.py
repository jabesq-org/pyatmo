"""Support for a Netatmo account."""
from __future__ import annotations

import logging
from abc import ABC
from typing import TYPE_CHECKING

from pyatmo.const import _GETHOMESDATA_REQ, _GETHOMESTATUS_REQ, _SETSTATE_REQ
from pyatmo.helpers import extract_raw_data_new
from pyatmo.home import NetatmoHome

if TYPE_CHECKING:
    from pyatmo.auth import AbstractAsyncAuth

LOG = logging.getLogger(__name__)


class AbstractAccount(ABC):
    """Abstract class of a Netatmo account."""

    auth: AbstractAsyncAuth
    user: str | None
    homes: dict[str, NetatmoHome]
    raw_data: dict

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(user={self.user}, home_ids={self.homes.keys()}"
        )

    def process_topology(self) -> None:
        """Process topology information from /homesdata."""
        for home in self.raw_data["homes"]:
            if (home_id := home["id"]) in self.homes:
                self.homes[home_id].update_topology(home)
            else:
                self.homes[home_id] = NetatmoHome(self.auth, raw_data=home)


class AsyncAccount(AbstractAccount):
    """Async class of a Netatmo account."""

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize the Netatmo account.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        self.auth = auth
        self.homes = {}

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

    async def async_set_state(self, home_id: str, data: dict) -> None:
        """Modify device state by passing JSON specific to the device."""
        LOG.debug("Setting state: %s", data)

        post_params = {
            "json": {
                "home": {
                    "id": home_id,
                    **data,
                },
            },
        }
        resp = await self.auth.async_post_request(url=_SETSTATE_REQ, params=post_params)
        LOG.debug("Response: %s", resp)
