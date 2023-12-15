"""Collection of helper functions."""
from __future__ import annotations

import logging
from typing import Any, cast

from pyatmo.const import RawData
from pyatmo.exceptions import NoDevice

LOG: logging.Logger = logging.getLogger(__name__)


def fix_id(raw_data: RawData) -> dict[str, Any]:
    """Fix known errors in station ids like superfluous spaces."""

    if not raw_data:
        return raw_data

    for station in raw_data:
        if not isinstance(station, dict):
            continue
        if station.get("_id") is None:
            continue

        station["_id"] = cast(dict, station)["_id"].replace(" ", "")

        for module in station.get("modules", {}):
            module["_id"] = module["_id"].replace(" ", "")

    return raw_data


def extract_raw_data(resp: Any, tag: str) -> dict[str, Any]:
    """Extract raw data from server response."""
    raw_data = {}

    if tag == "body":
        return {"public": resp["body"], "errors": []}

    if resp is None or "body" not in resp or tag not in resp["body"]:
        LOG.debug("Server response: %s", resp)
        raise NoDevice("No device found, errors in response")

    if tag == "homes":
        return {
            tag: fix_id(resp["body"].get(tag)),
            "errors": resp["body"].get("errors", []),
        }

    if not (raw_data := fix_id(resp["body"].get(tag))):
        LOG.debug("Server response: %s", resp)
        raise NoDevice("No device data available")

    return {tag: raw_data, "errors": resp["body"].get("errors", [])}
