"""Collection of helper functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pyatmo.exceptions import NoDeviceError

if TYPE_CHECKING:
    from pyatmo.const import RawData

LOG: logging.Logger = logging.getLogger(__name__)


def str_or_none(value: Any) -> str | None:  # noqa: ANN401
    """Return `value` if it is a string, else `None`.

    Raw Netatmo scalars are not guaranteed to match their documented type.
    Treating a wrongly-typed one as absent keeps unhashable values out of the
    `home`/`room`/`module` id lookups, which would otherwise raise `TypeError`,
    and keeps them off the model. Webhook payloads are the harshest case, since
    they are caller-supplied and arrive from a public endpoint.
    """
    if isinstance(value, str):
        return value
    if value is not None:
        LOG.debug("Discarding non-string value: %r", value)
    return None


def number_or_none(value: Any) -> float | None:  # noqa: ANN401
    """Return `value` if it is a real number, else `None`.

    `bool` is rejected even though it is an `int` subclass: it is never a real
    measurement, and letting it through would store `True` as a temperature.
    Numeric strings are rejected too rather than parsed, so a wrongly-typed
    payload cannot overwrite a known-good reading.
    """
    if isinstance(value, int | float) and not isinstance(value, bool):
        return value
    if value is not None:
        LOG.debug("Discarding non-numeric value: %r", value)
    return None


def dict_entries(value: Any) -> list[dict[str, Any]]:  # noqa: ANN401
    """Return only the dict entries of a raw list, tolerating malformed input.

    Netatmo webhook payloads are caller-supplied and arrive from a public
    endpoint, so a list field may be absent, `null`, or hold anything at all.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def fix_id(raw_data: list[RawData | str]) -> list[RawData | str]:
    """Fix known errors in station ids like superfluous spaces."""

    if not raw_data:
        return raw_data

    for station in dict_entries(raw_data):
        if station.get("_id") is None:
            continue

        station["_id"] = station["_id"].replace(" ", "")

        for module in station.get("modules", []):
            module["_id"] = module["_id"].replace(" ", "")

    return raw_data


def home_suffix(home_id: str | None) -> str:
    """Return ``" for home <id>"`` for a home id, else ``""``.

    Shared by every log line and error message that can name a home, so the
    wording stays identical across modules and an absent home id costs no
    trailing noise.
    """
    return f" for home {home_id}" if home_id else ""


def extract_raw_data(resp: RawData, tag: str, home_id: str | None = None) -> RawData:
    """Extract raw data from server response.

    ``home_id`` is optional and used solely to name the home the request was
    for: the id travels in the request body, never in the response, so a
    body-less 200 is otherwise unattributable on a multi-home account.
    """
    if tag == "body":
        return {"public": resp["body"], "errors": []}

    suffix: str = home_suffix(home_id)

    if resp is None or "body" not in resp or tag not in resp["body"]:
        LOG.debug("Server response (tag: %s)%s: %s", tag, suffix, resp)
        msg = f"No device found, errors in response{suffix}"
        raise NoDeviceError(msg)

    if tag == "homes":
        homes: list[RawData | str] = fix_id(resp["body"].get(tag))
        if not homes:
            LOG.debug("Server response (tag: %s)%s: %s", tag, suffix, resp)
            msg = f"No homes found{suffix}"
            raise NoDeviceError(msg)
        return {
            tag: homes,
            "errors": resp["body"].get("errors", []),
        }

    if not (raw_data := fix_id(resp["body"].get(tag))):
        LOG.debug("Server response (tag: %s)%s: %s", tag, suffix, resp)
        msg = f"No device data available{suffix}"
        raise NoDeviceError(msg)

    return {tag: raw_data, "errors": resp["body"].get("errors", [])}
