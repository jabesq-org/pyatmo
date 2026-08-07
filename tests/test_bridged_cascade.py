"""Tests for the bridged-children cascade in `Module.update`.

The cascade is the block that re-runs `update()` on a module's bridged children,
and on those children's rooms, passing the *parent's* payload, whenever the parent
resolves falsy `reachable`. These tests use the capture-derived `realshape` home,
whose `/homesdata` carries no `reachable` key on any module — as the real API does —
so the bridges resolve `None` and the cascade actually fires.

See docs/superpowers/specs/2026-08-07-bridged-cascade-design.md.
"""

STATION = "12:34:56:aa:01:01"
RELAY = "12:34:56:aa:07:07"
AIR_CONDITIONER = "12:34:56:aa:11:11"

# Holds only the rain gauge and the outdoor module, both bridged to the station,
# and is absent from the /homestatus rooms list.
UNREPORTED_BRIDGED_ROOM = "100006"
# Holds the camera and the relay. Nothing bridges into it and it is likewise absent
# from the /homestatus rooms list, so it never gets updated at all.
UNREPORTED_ISOLATED_ROOM = "100001"


async def test_homesdata_reports_no_reachability(async_account_realshape):
    """Precondition: /homesdata alone leaves every module's reachability unknown.

    The real API never sends `reachable` in /homesdata. `homesdata.json` does, which
    is why the cascade is invisible in the rest of the suite.
    """
    home = async_account_realshape.homes["realshape_home_id"]
    assert {module.reachable for module in home.modules.values()} == {None}


async def test_bridges_resolve_unknown_and_so_cascade(async_home_realshape):
    """Precondition: both bridges stay unknown after /homestatus, so the cascade fires.

    Neither bridge reports `reachable` in either endpoint. `None` is falsy, so
    `if not self.reachable and self.modules` in `Module.update` is satisfied and each
    bridge pushes its own payload down. Their children do report `reachable`, so they
    resolve `True` on their own entries.
    """
    home = async_home_realshape

    for bridge_id in (STATION, RELAY):
        bridge = home.modules[bridge_id]
        assert bridge.reachable is None
        assert bridge.modules
        for child_id in bridge.modules:
            assert home.modules[child_id].reachable is True

    # A module with no bridged children resolves unknown but cannot cascade.
    assert home.modules[AIR_CONDITIONER].reachable is None
    assert not home.modules[AIR_CONDITIONER].modules


async def test_unreported_room_is_contaminated_by_the_cascade(async_home_realshape):
    """Characterization: an unreported room holds its bridge's readings, not its own.

    The cascade calls `Room.update()` with the *station's* payload, so the humidity
    below is the weather station's reading, in a room that has no humidity sensor of
    its own. `radiators_power` is set to 0 unconditionally by `Room.update`.

    The isolated room is the control: same absence from /homestatus, but nothing
    bridges into it, so it keeps its defaults.

    Both assertions invert once the cascade is removed — the contaminated room should
    end up looking like the control.
    """
    home = async_home_realshape

    contaminated = home.rooms[UNREPORTED_BRIDGED_ROOM]
    assert contaminated.humidity == 37
    assert contaminated.radiators_power == 0

    control = home.rooms[UNREPORTED_ISOLATED_ROOM]
    assert control.humidity is None
    assert control.radiators_power is None
