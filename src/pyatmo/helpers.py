"""Collection of helper functions."""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from pyatmo.const import RawData
from pyatmo.exceptions import NoDeviceError

LOG: logging.Logger = logging.getLogger(__name__)

ATTRIBUTES_TO_FIX: dict[str, str] = {
    "firmware": "firmware_revision",
    "wifi_status": "wifi_strength",
    "rf_status": "rf_strength",
    "Temperature": "temperature",
    "Humidity": "humidity",
    "Pressure": "pressure",
    "CO2": "co2",
    "AbsolutePressure": "absolute_pressure",
    "Noise": "noise",
    "Rain": "rain",
    "WindStrength": "wind_strength",
    "WindAngle": "wind_angle",
    "GustStrength": "gust_strength",
    "GustAngle": "gust_angle",
    "wind_gust": "gust_strength",
    "wind_gust_angle": "gust_angle",
}

T = TypeVar("T", RawData, list)


def _normalize_value(value: T) -> T:
    """Recursively normalize a value (handles nested dicts and lists)."""
    if isinstance(value, dict):
        return _normalize_dict(value)
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _normalize_dict(raw_data: RawData) -> RawData:
    """Normalize a dictionary's weather-related attributes."""
    normalized: RawData = {}
    for key, value in raw_data.items():
        if key == "_id":
            normalized["_id"] = value
            continue
        if key == "dashboard_data" and isinstance(value, dict):
            normalized |= _normalize_dict(value)
            continue

        mapped_key = ATTRIBUTES_TO_FIX.get(key, key)
        normalized[mapped_key] = _normalize_value(value)

    if "_id" in normalized and "id" not in normalized:
        normalized["id"] = normalized["_id"]
    return normalized


def normalize_weather_attributes(raw_data: RawData) -> RawData:
    """Normalize weather attributes.

    Transforms API response attribute names to standardized names
    and flattens dashboard_data into the parent dictionary.
    """
    return _normalize_dict(raw_data)


def fix_id(raw_data: list[RawData | str]) -> list[RawData | str]:
    """Fix known errors in station ids like superfluous spaces."""

    if not raw_data:
        return raw_data

    for station in raw_data:
        if not isinstance(station, dict):
            continue
        if station.get("_id") is None:
            continue

        station["_id"] = station["_id"].replace(" ", "")

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

    body = resp["body"]
    tag_data = body.get(tag, [])
    normalized_data = [
        normalize_weather_attributes(item)
        for item in tag_data
        if isinstance(item, dict)
    ]

    if tag == "homes":
        homes: list[dict[str, Any] | str] = fix_id(normalized_data)
        if not homes:
            LOG.debug("Server response (tag: %s): %s", tag, resp)
            msg = "No homes found"
            raise NoDeviceError(msg)
        return {
            tag: homes,
            "errors": body.get("errors", []),
        }

    if not (raw_data := fix_id(normalized_data)):
        LOG.debug("Server response (tag: %s): %s", tag, resp)
        msg = "No device data available"
        raise NoDeviceError(msg)

    return {tag: raw_data, "errors": body.get("errors", [])}
