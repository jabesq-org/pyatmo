"""Tests for the bridged-children cascade in `Module.update`.

The cascade is the block that re-runs `update()` on a module's bridged children,
and on those children's rooms, passing the *parent's* payload, whenever the parent
resolves falsy `reachable`. These tests use the capture-derived AC home, whose
`/homesdata` carries no `reachable` key on any module — as the real API does — so
the bridges resolve `None` and the cascade actually fires.

See docs/superpowers/specs/2026-08-07-bridged-cascade-design.md.
"""

STATION = "12:34:56:ac:00:01"
RELAY = "12:34:56:ac:00:07"
AIR_CONDITIONER = "12:34:56:ac:00:11"
# Bridged to the station, in the balcony, and reports its own temperature.
OUTDOOR = "12:34:56:ac:00:04"

# Holds only the rain gauge and the outdoor module, both bridged to the station,
# and is absent from the /homestatus rooms list.
UNREPORTED_BRIDGED_ROOM = "ac_room_balcony"
# Holds the camera and the relay. Nothing bridges into it and it is likewise absent
# from the /homestatus rooms list, so it never gets updated at all.
UNREPORTED_ISOLATED_ROOM = "ac_room_entry"


async def test_homesdata_reports_no_reachability(async_account_ac):
    """Precondition: /homesdata alone leaves every module's reachability unknown.

    The real API never sends `reachable` in /homesdata. `homesdata.json` does, which
    is why the cascade is invisible in the rest of the suite.
    """
    home = async_account_ac.homes["ac_home_id"]
    assert {module.reachable for module in home.modules.values()} == {None}


async def test_bridges_resolve_unknown_and_so_cascade(async_home_ac):
    """Precondition: both bridges stay unknown after /homestatus, so the cascade fires.

    Neither bridge reports `reachable` in either endpoint. `None` is falsy, so
    `if not self.reachable and self.modules` in `Module.update` is satisfied and each
    bridge pushes its own payload down. Their children do report `reachable`, so they
    resolve `True` on their own entries.
    """
    home = async_home_ac

    for bridge_id in (STATION, RELAY):
        bridge = home.modules[bridge_id]
        assert bridge.reachable is None
        assert bridge.modules
        for child_id in bridge.modules:
            assert home.modules[child_id].reachable is True

    # A module with no bridged children resolves unknown but cannot cascade.
    assert home.modules[AIR_CONDITIONER].reachable is None
    assert not home.modules[AIR_CONDITIONER].modules


async def test_unreported_room_is_contaminated_by_the_cascade(async_home_ac):
    """Characterization: an unreported room holds its bridge's readings, not its own.

    The cascade calls `Room.update()` with the *station's* payload, so the readings
    below are the indoor weather station's, in an outdoor room that has no CO2 or
    humidity sensor of its own. `radiators_power` is set to 0 unconditionally by
    `Room.update`.

    The isolated room is the control: same absence from /homestatus, but nothing
    bridges into it, so it keeps its defaults.

    Both assertions invert once the cascade is removed — the contaminated room should
    end up looking like the control.
    """
    home = async_home_ac

    contaminated = home.rooms[UNREPORTED_BRIDGED_ROOM]
    assert contaminated.co2 == 421
    assert contaminated.humidity == 37
    assert contaminated.temperature == 25
    assert contaminated.radiators_power == 0

    control = home.rooms[UNREPORTED_ISOLATED_ROOM]
    assert control.co2 is None
    assert control.humidity is None
    assert control.temperature is None
    assert control.radiators_power is None


async def test_cascade_leaves_the_bridged_module_itself_alone(async_home_ac):
    """The cascade corrupts the room, not the module whose room it is.

    The outdoor module lives in the contaminated room and is one of the children the
    station pushes its payload to, yet `Module.update` is called with that payload and
    still resolves the module's own entry. This assertion must survive the fix — it is
    what separates "the room got the wrong readings" from "the module did".
    """
    outdoor = async_home_ac.modules[OUTDOOR]
    assert outdoor.bridge == STATION
    assert outdoor.room_id == UNREPORTED_BRIDGED_ROOM
    assert outdoor.temperature == 26.4
