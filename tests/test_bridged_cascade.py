"""Tests for the removal of the bridged-children cascade.

`Module.update` used to re-run `update()` on a module's bridged children, and on
those children's rooms, passing the *parent's* payload, whenever the parent resolved
falsy `reachable`. No real bridge reports `reachable`, so `None` is what it resolved,
`not None` is `True`, and the block fired on a healthy bridge every poll.

Rooms present in `/homestatus` were repaired moments later by the rooms loop. Rooms
absent from it were not, and kept the bridge's readings forever. These tests use two
capture-derived homes, from different accounts, that both have that shape.
"""

from unittest.mock import AsyncMock, patch

from tests.common import MockResponse

STATION = "12:34:56:ac:00:01"
RELAY = "12:34:56:ac:00:07"
AIR_CONDITIONER = "12:34:56:ac:00:11"
# Bridged to the station, in the balcony, and reports its own temperature.
OUTDOOR = "12:34:56:ac:00:04"

# Declared in /homesdata but absent from the /homestatus rooms list. The balcony holds
# two of the station's bridged children, so the cascade used to reach it; nothing
# bridges into the entry, which is why it was the control.
AC_UNREPORTED_ROOMS = ("ac_room_balcony", "ac_room_entry")

# The second capture, from a different account, with the same shape.
BRIDGED_STATION = "12:34:56:bb:00:01"
BRIDGED_UNREPORTED_ROOMS = ("bridged_room_outdoor", "bridged_room_bedroom")

# The Legrand gateway of the main fixture bridges two modules whose `room_id` is not in
# `home.rooms`. Reaching them through the cascade raised KeyError out of
# `async_update_status`.
MAIN_HOME = "91763b24c43d3e344f424e8b"
MAIN_GATEWAY = "12:34:56:80:60:40"


async def test_homesdata_reports_no_reachability(async_account_ac):
    """Precondition: /homesdata alone leaves every module's reachability unknown.

    The real API never sends `reachable` in /homesdata. `homesdata.json` does, on 5 of
    its 51 modules, which is why the cascade was invisible in most of the suite.
    """
    home = async_account_ac.homes["ac_home_id"]
    assert {module.reachable for module in home.modules.values()} == {None}


async def test_a_module_without_bridged_children_never_cascaded(async_home_ac):
    """The air conditioner is the case the old block could not reach either way.

    It has no bridged children, so `and self.modules` was always false for it. Kept as
    the negative half of the removed condition.
    """
    assert not async_home_ac.modules[AIR_CONDITIONER].modules


def assert_rooms_kept_their_defaults(home, room_ids):
    """Assert none of `room_ids` was ever handed a module payload.

    `radiators_power` is the sharpest probe: `Room.update` sets it to 0 unconditionally
    while the dataclass default is `None`, so `None` proves the method never ran.
    """
    for room_id in room_ids:
        room = home.rooms[room_id]
        assert room.co2 is None, room_id
        assert room.humidity is None, room_id
        assert room.temperature is None, room_id
        assert room.radiators_power is None, room_id


async def test_unreported_room_is_not_fed_the_bridge_payload(async_home_ac):
    """A room absent from /homestatus keeps its defaults, bridged into or not.

    The balcony used to hold the indoor station's `co2 == 421`, `humidity == 37` and
    `temperature == 25` because the station bridges two modules that live there. It now
    looks like the entry, the room nothing bridges into, which is the point of the
    change.
    """
    assert_rooms_kept_their_defaults(async_home_ac, AC_UNREPORTED_ROOMS)


async def test_unreported_room_is_not_fed_the_bridge_payload_second_capture(
    async_home_bridged,
):
    """The same assertion on a second home, captured from a different account.

    Its outdoor room used to report the indoor station's `co2 == 226`,
    `humidity == 47` and `temperature == 23.6`. This exists to show the behaviour was a
    property of the API's shape rather than of one capture.
    """
    assert_rooms_kept_their_defaults(async_home_bridged, BRIDGED_UNREPORTED_ROOMS)


async def test_bridged_module_keeps_its_own_readings(async_home_ac):
    """The outdoor module reports its own temperature, not the station's.

    It lives in the room the cascade used to damage and is one of the children the
    station pushed its payload to. This assertion was true before the change and must
    stay true after it -- it is what separates "the room got the wrong readings" from
    "the module did".
    """
    outdoor = async_home_ac.modules[OUTDOOR]
    assert outdoor.bridge == STATION
    assert outdoor.room_id == AC_UNREPORTED_ROOMS[0]
    assert outdoor.temperature == 26.4


async def test_errors_naming_a_bridge_with_unmapped_rooms_does_not_raise(async_account):
    """Regression: `errors[]` on a gateway whose children sit in unmapped rooms.

    `mark_unreachable()` made the gateway falsy, the cascade then walked its 16
    bridged children, and `self.home.rooms[module.room_id]` raised `KeyError` for the
    two whose `room_id` is absent from `home.rooms` -- out of `async_update_status`,
    where a caller has no way to handle it.
    """
    await async_account.async_update_status(MAIN_HOME)
    home = async_account.homes[MAIN_HOME]

    unmapped = {
        module.room_id
        for module_id in home.modules[MAIN_GATEWAY].modules
        if (module := home.modules[module_id]).room_id
        and module.room_id not in home.rooms
    }
    assert unmapped, "fixture no longer has bridged children in unmapped rooms"

    outage = {
        "status": "ok",
        "body": {
            "home": {"id": MAIN_HOME, "modules": []},
            "errors": [{"code": 3, "id": MAIN_GATEWAY}],
        },
    }
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(outage, 200)),
    ):
        await async_account.async_update_status(MAIN_HOME)

    # The mark still propagates: that work belongs to mark_unreachable(), not the
    # cascade, so it survives the removal.
    assert home.modules[MAIN_GATEWAY].reachable is False
    for module_id in home.modules[MAIN_GATEWAY].modules:
        if "#" not in module_id:
            assert home.modules[module_id].reachable is False, module_id
