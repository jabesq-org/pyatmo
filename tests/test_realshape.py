"""Sanity tests for the capture-derived `realshape` home fixtures.

These fixtures are anonymized from a real API response pair. Unlike `homesdata.json`,
their `/homesdata` carries no `reachable` key on any module — which is what the real
API does — so they exercise reachability resolution realistically.

Behaviour that depends on that shape is tested in `test_bridged_cascade.py`. This
module only checks that the fixtures parse into the topology they are meant to
describe, so a future edit to them fails loudly here.
"""

from pyatmo import DeviceType

HOME_ID = "realshape_home_id"
STATION = "12:34:56:aa:01:01"
CAMERA = "12:34:56:aa:06:06"
RELAY = "12:34:56:aa:07:07"
AIR_CONDITIONER = "12:34:56:aa:11:11"

# Declared in /homesdata but absent from the /homestatus rooms list.
UNREPORTED_ROOMS = {"100001", "100006"}


async def test_realshape_topology(async_account_realshape):
    """The home parses, with both bridges and their bridged children."""
    home = async_account_realshape.homes[HOME_ID]
    assert len(home.modules) == 11
    assert len(home.rooms) == 6

    station = home.modules[STATION]
    assert station.device_type == DeviceType.NAMain
    assert len(station.modules) == 4

    relay = home.modules[RELAY]
    assert relay.device_type == DeviceType.NAPlug
    assert len(relay.modules) == 3
    for module_id in relay.modules:
        assert home.modules[module_id].device_type == DeviceType.NRV

    # A standalone module: no bridge of its own and no bridged children.
    camera = home.modules[CAMERA]
    assert camera.device_type == DeviceType.NACamera
    assert camera.bridge is None
    assert not camera.modules

    assert home.modules[AIR_CONDITIONER].device_type == DeviceType.NAC


async def test_realshape_rooms_absent_from_status(async_home_realshape):
    """Two rooms exist in /homesdata but are absent from the /homestatus rooms list."""
    for room_id, room in async_home_realshape.rooms.items():
        assert room.reachable is (None if room_id in UNREPORTED_ROOMS else True)


async def test_realshape_schedules(async_account_realshape):
    """All five schedules parse, across therm, cooling and auto types."""
    home = async_account_realshape.homes[HOME_ID]
    assert len(home.schedules) == 5
    assert {schedule.type for schedule in home.schedules.values()} == {
        "therm",
        "cooling",
        "auto",
    }
