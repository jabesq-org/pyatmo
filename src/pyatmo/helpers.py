"""Collection of helper functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from pyatmo.exceptions import NoDeviceError

if TYPE_CHECKING:
    from pyatmo.const import RawData

LOG: logging.Logger = logging.getLogger(__name__)


def fix_id(raw_data: list[RawData | str]) -> list[RawData | str]:
    """Fix known errors in station ids like superfluous spaces."""

    if not raw_data:
        return raw_data

    for station in raw_data:
        if not isinstance(station, dict):
            continue
        if station.get("_id") is None:
            continue

        station["_id"] = cast("dict", station)["_id"].replace(" ", "")

        for module in station.get("modules", {}):
            module["_id"] = module["_id"].replace(" ", "")

    return raw_data


def extract_raw_data(resp: RawData, tag: str) -> RawData:
    """Extract raw data from server response."""
    if tag == "body":
        return {"public": resp["body"], "errors": []}

    if resp is None or "body" not in resp or tag not in resp["body"]:
        LOG.debug("Server response (tag: %s): %s", tag, resp)
        msg = "No device found, errors in response"
        raise NoDeviceError(msg)

    if tag == "homes":
        homes: list[dict[str, Any] | str] = fix_id(resp["body"].get(tag))
        if not homes:
            LOG.debug("Server response (tag: %s): %s", tag, resp)
            msg = "No homes found"
            raise NoDeviceError(msg)
        return {
            tag: homes,
            "errors": resp["body"].get("errors", []),
        }

    if not (raw_data := fix_id(resp["body"].get(tag))):
        LOG.debug("Server response (tag: %s): %s", tag, resp)
        msg = "No device data available"
        raise NoDeviceError(msg)

    return {tag: raw_data, "errors": resp["body"].get("errors", [])}
