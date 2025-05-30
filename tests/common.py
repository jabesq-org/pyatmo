"""Define shared test helpers."""

from __future__ import annotations

import json
import pathlib


def get_fixture_path(filename: str) -> pathlib.Path:
    """Get path of fixture."""
    return pathlib.Path(__file__).parent.joinpath("../fixtures", filename)


def load_fixture(filename):
    """Load a fixture."""
    return get_fixture_path(filename).read_text(encoding="utf-8")


class MockResponse:
    def __init__(self, text, status):
        self._text = text
        self.status = status

    async def json(self):
        return self._text

    async def read(self):
        return self._text

    async def __aexit__(self, exc_type, exc, traceback):
        pass

    async def __aenter__(self):
        return self


async def fake_post_request(*_, **kwargs):
    """Return fake data."""
    if "endpoint" not in kwargs:
        return "{}"

    endpoint = kwargs["endpoint"].split("/")[-1]

    if endpoint in "snapshot_720.jpg":
        return b"test stream image bytes"

    if endpoint in [
        "setpersonsaway",
        "setpersonshome",
        "setstate",
        "setroomthermpoint",
        "setthermmode",
        "switchhomeschedule",
    ]:
        payload = f'{{"{endpoint}": true}}'

    elif endpoint == "homestatus":
        home_id = kwargs.get("params", {}).get("home_id")
        payload = json.loads(load_fixture(f"{endpoint}_{home_id}.json"))

    elif endpoint == "getmeasure":
        module_id = kwargs.get("params", {}).get("module_id", "")
        measure_type = kwargs.get("params", {}).get("type", "")
        payload = json.loads(
            load_fixture(
                f"{endpoint}_{measure_type}_{module_id.replace(':', '_')}.json",
            ),
        )

    else:
        postfix = kwargs.get("POSTFIX")
        if postfix is not None:
            payload = json.loads(load_fixture(f"{endpoint}_{postfix}.json"))
        else:
            payload = json.loads(load_fixture(f"{endpoint}.json"))

    return MockResponse(payload, 200)


async def fake_post_request_multi(*args, **kwargs):
    kwargs["POSTFIX"] = "multi"
    return await fake_post_request(*args, **kwargs)
