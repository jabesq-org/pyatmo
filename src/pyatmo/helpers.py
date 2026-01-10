"""Collection of helper functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from pyatmo.exceptions import NoDeviceError

if TYPE_CHECKING:
    from pyatmo.const import RawData

LOG: logging.Logger = logging.getLogger(__name__)

# types for data that can be normalized (recursive structures) - to satisfy mypy
NormalizableData = dict[str, Any] | list[Any] | str | int | float | bool | None

ATTRIBUTES_TO_FIX: dict[str, str] = {
    "firmware": "firmware_revision",
    "firmware_revision": "firmware_revision",
    "firmware_name": "firmware_name",
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


def normalize_weather_attributes(raw_data: NormalizableData) -> NormalizableData:
    """Normalize weather-related attributes recursively."""

    if isinstance(raw_data, list):
        return [normalize_weather_attributes(item) for item in raw_data]

    if not isinstance(raw_data, dict):
        return raw_data

    normalized: dict[str, Any] = {}
    for key, value in raw_data.items():
        if key == "_id":
            normalized["_id"] = value
            continue
        if key == "dashboard_data" and isinstance(value, dict):
            # useless cast here to satisfy mypy
            normalized |= cast("dict[str, Any]", normalize_weather_attributes(value))
            continue

        mapped_key = ATTRIBUTES_TO_FIX[key] if key in ATTRIBUTES_TO_FIX else key  # noqa: SIM401
        normalized[mapped_key] = normalize_weather_attributes(value)

    if "_id" in normalized and "id" not in normalized:
        normalized["id"] = normalized["_id"]
    return normalized


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

    # useless cast here again to satisfy mypy
    body = cast("dict[str, Any]", normalize_weather_attributes(resp["body"]))

    if tag == "homes":
        homes: list[dict[str, Any] | str] = fix_id(body.get(tag, []))
        if not homes:
            LOG.debug("Server response (tag: %s): %s", tag, resp)
            msg = "No homes found"
            raise NoDeviceError(msg)
        return {
            tag: homes,
            "errors": body.get("errors", []),
        }

    if not (raw_data := fix_id(body.get(tag, []))):
        LOG.debug("Server response (tag: %s): %s", tag, resp)
        msg = "No device data available"
        raise NoDeviceError(msg)

    return {tag: raw_data, "errors": body.get("errors", [])}
