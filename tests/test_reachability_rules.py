"""Tests for how `Module.reachable` is resolved.

Three rules combine, and which one applies is decided by the *shape* of a module's
`/homestatus` entry rather than by its device type:

* the entry reports `reachable` -- use it;
* the entry omits it and the id is `#`-suffixed -- resolve from the parent module;
* the entry omits it and the module is a root -- presence in `/homestatus` is the only
  signal the API gives, so treat presence as reachable.

Across three real accounts every bridged module reports the key and no `#`-suffixed
sub-module does, which is what makes the third rule safe to key on shape.
"""

from unittest.mock import AsyncMock, patch

from tests.common import MockResponse

HOME_ID = "91763b24c43d3e344f424e8b"

# A Legrand ecometer: a root module that reports only `firmware_revision` and
# `wifi_strength`, plus nine `#`-suffixed sub-meters that report nothing but `bridge`.
ECOMETER = "12:34:56:00:16:0e"
SUB_METERS = [f"{ECOMETER}#{index}" for index in range(9)]


async def test_root_module_without_the_key_resolves_reachable(async_home_ac):
    """A bridge that never reports `reachable` reads as reachable, not unknown.

    Both bridges of this home omit the key in `/homesdata` and `/homestatus`. They are
    present in the status payload, so presence is the signal. Their bridged children do
    report the key and resolve it from their own entries.
    """
    home = async_home_ac

    for bridge_id in ("12:34:56:ac:00:01", "12:34:56:ac:00:07"):
        bridge = home.modules[bridge_id]
        assert bridge.bridge is None
        assert bridge.reachable is True
        for child_id in bridge.modules:
            assert home.modules[child_id].reachable is True


async def test_ecometer_and_its_sub_meters_resolve_reachable(async_home):
    """The NLE bridge stores `True`; its sub-meters stay unset and follow the parent.

    The distinction matters. A value written onto a `#`-suffixed sub-meter would stop it
    consulting its parent, and `mark_unreachable()` skips `#` ids by design, so the
    write could never be cleared -- the sub-meters would hold a stale `True` through an
    outage. Leaving them unset is what lets them follow the bridge down.
    """
    bridge = async_home.modules[ECOMETER]
    assert bridge.reachable is True
    assert bridge._reachable is True  # noqa: SLF001

    assert set(bridge.modules) == set(SUB_METERS)
    for sub_meter_id in SUB_METERS:
        sub_meter = async_home.modules[sub_meter_id]
        assert sub_meter.reachable is True
        assert sub_meter._reachable is None, sub_meter_id  # noqa: SLF001


async def test_ecometer_outage_takes_its_sub_meters_down(async_account):
    """An errored NLE bridge resolves `False` and its nine sub-meters follow it.

    This pins both halves of the rule at once: the non-empty `raw_data` guard stops the
    `errors[]` path's `update({})` from stamping the bridge reachable again, and leaving
    the sub-meters unset is what lets them resolve `False` through the parent.
    """
    await async_account.async_update_status(HOME_ID)
    home = async_account.homes[HOME_ID]
    assert home.modules[ECOMETER].reachable is True

    outage = {
        "status": "ok",
        "body": {
            "home": {"id": HOME_ID, "modules": []},
            "errors": [{"code": 3, "id": ECOMETER}],
        },
    }
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(outage, 200)),
    ):
        await async_account.async_update_status(HOME_ID)

    assert home.modules[ECOMETER].reachable is False
    for sub_meter_id in SUB_METERS:
        assert home.modules[sub_meter_id].reachable is False, sub_meter_id


async def test_a_reported_false_wins_over_presence(async_account):
    """A module that reports `reachable: false` stays unreachable.

    The presence rule fires only when the key is absent, so it can never overwrite what
    the API actually said. Without that condition this would read `True`.
    """
    await async_account.async_update_status(HOME_ID)
    home = async_account.homes[HOME_ID]

    payload = {
        "status": "ok",
        "body": {
            "home": {
                "id": HOME_ID,
                "modules": [{"id": ECOMETER, "type": "NLE", "reachable": False}],
            },
        },
    }
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(payload, 200)),
    ):
        await async_account.async_update_status(HOME_ID)

    assert home.modules[ECOMETER].reachable is False


async def test_mark_unreachable_survives_a_cycle_in_modules_bridged(async_home):
    """`modules_bridged` is unvalidated API data, so the walk must tolerate a cycle.

    Two modules naming each other used to recurse until the stack ran out, raising
    `RecursionError` from inside `async_update_status`.
    """
    first = async_home.modules["12:34:56:00:fa:d0"]
    second = async_home.modules["12:34:56:80:60:40"]
    first.modules = [second.entity_id]
    second.modules = [first.entity_id]

    first.mark_unreachable()

    assert first.reachable is False
    assert second.reachable is False


async def test_sub_module_keeps_its_own_reported_value(async_account):
    """An explicit value on a `#`-suffixed sub-module beats the parent's.

    The parent fallback in `reachable` is a fallback, not an override: it only applies
    when the sub-module has no value of its own.
    """
    await async_account.async_update_status(HOME_ID)
    home = async_account.homes[HOME_ID]

    payload = {
        "status": "ok",
        "body": {
            "home": {
                "id": HOME_ID,
                "modules": [
                    {"id": ECOMETER, "type": "NLE", "reachable": True},
                    {"id": SUB_METERS[0], "type": "NLE", "reachable": False},
                ],
            },
        },
    }
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(payload, 200)),
    ):
        await async_account.async_update_status(HOME_ID)

    assert home.modules[ECOMETER].reachable is True
    assert home.modules[SUB_METERS[0]].reachable is False
    assert home.modules[SUB_METERS[1]].reachable is True
