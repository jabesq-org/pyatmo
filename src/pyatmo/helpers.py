"""Collection of helper functions."""
from __future__ import annotations

import logging
import time
from calendar import timegm
from datetime import datetime
from typing import Any

from pyatmo.const import RawData
from pyatmo.exceptions import NoDevice

LOG: logging.Logger = logging.getLogger(__name__)


def to_time_string(value: str) -> str:
    return datetime.utcfromtimestamp(int(value)).isoformat(sep="_")


def to_epoch(value: str) -> int:
    return timegm(time.strptime(f"{value}GMT", "%Y-%m-%d_%H:%M:%S%Z"))


def today_stamps() -> tuple[int, int]:
    today: int = timegm(time.strptime(time.strftime("%Y-%m-%d") + "GMT", "%Y-%m-%d%Z"))
    return today, today + 3600 * 24


def fix_id(raw_data: RawData) -> dict[str, Any]:
    """Fix known errors in station ids like superfluous spaces."""
    if not raw_data:
        return raw_data

    for station in raw_data:
        if not isinstance(station, dict):
            continue
        if "_id" not in station:
            continue

        station["_id"] = station["_id"].replace(" ", "")

        for module in station.get("modules", {}):
            module["_id"] = module["_id"].replace(" ", "")

    return raw_data


def extract_raw_data(resp: Any, tag: str) -> dict[str, Any]:
    """Extract raw data from server response."""
    if (
        resp is None
        or "body" not in resp
        or tag not in resp["body"]
        or ("errors" in resp["body"] and "modules" not in resp["body"][tag])
    ):
        LOG.debug("Server response: %s", resp)
        raise NoDevice("No device found, errors in response")

    if not (raw_data := fix_id(resp["body"].get(tag))):
        LOG.debug("Server response: %s", resp)
        raise NoDevice("No device data available")

    return raw_data


def extract_raw_data_new(resp: Any, tag: str) -> dict[str, Any]:
    """Extract raw data from server response."""
    raw_data = {}

    if tag == "body":
        return {"public": resp["body"], "errors": []}

    if resp is None or "body" not in resp or tag not in resp["body"]:
        LOG.debug("Server response: %s", resp)
        raise NoDevice("No device found, errors in response")

    if not (raw_data := fix_id(resp["body"].get(tag))):
        LOG.debug("Server response: %s", resp)
        raise NoDevice("No device data available")

    return {tag: raw_data, "errors": resp["body"].get("errors", [])}
