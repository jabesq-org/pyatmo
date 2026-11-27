"""Define tests for the active zone of a schedule timetable."""

from datetime import UTC, datetime, timedelta, timezone
import logging

import pytest
import time_machine

from pyatmo.enums import TemperatureControlMode
from pyatmo.home import Home

# Selected (cooling) schedule of fixtures/homesdata.json, home in Europe/Berlin.
# Monday: Night from 00:00, Comfort from 06:00, Eco from 07:00, Comfort from
# 16:00, Night from 23:30. The last entry of the week is Night, Sunday 23:30.
# This room is set to 21 in Comfort, 17 in Night and 18 in Eco.
ROOM_ID = "2746182631"

# 2026-10-26 is a Monday, the day after Europe/Berlin left summer time.
MONDAY = datetime(2026, 10, 26)


def _home(
    async_auth,
    timetable: list[dict],
    zones: list[dict] | None = None,
    timezone_name: str | None = "Europe/Paris",
) -> Home:
    """Return a heating home whose selected schedule has the given timetable."""
    raw_data: dict = {
        "id": "schedule-home",
        "name": "Schedule Home",
        "temperature_control_mode": "heating",
        "schedules": [
            {
                "id": "sched",
                "name": "Daily",
                "type": "therm",
                "selected": True,
                "timetable": timetable,
                "zones": zones
                if zones is not None
                else [
                    {
                        "id": 0,
                        "name": "Comfort",
                        "type": 0,
                        "rooms": [{"id": "1", "therm_setpoint_temperature": 20}],
                    },
                    {
                        "id": 1,
                        "name": "Night",
                        "type": 1,
                        "rooms": [{"id": "1", "therm_setpoint_temperature": 17}],
                    },
                ],
            },
        ],
    }
    if timezone_name is not None:
        raw_data["timezone"] = timezone_name
    return Home(async_auth, raw_data)


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        (MONDAY, "Night"),
        (MONDAY + timedelta(hours=5, minutes=59), "Night"),
        (MONDAY + timedelta(hours=6), "Comfort"),
        (MONDAY + timedelta(hours=6, seconds=59), "Comfort"),
        (MONDAY + timedelta(hours=7), "Eco"),
        (MONDAY + timedelta(hours=15, minutes=59), "Eco"),
        (MONDAY + timedelta(hours=16), "Comfort"),
        (MONDAY + timedelta(hours=23, minutes=30), "Night"),
        # Wednesday 06:59 (m_offset 3240 is Comfort, 3300 is Eco).
        (MONDAY + timedelta(days=2, hours=6, minutes=59), "Comfort"),
        # Saturday 08:00 (m_offset 7620 is Comfort until 8610).
        (MONDAY + timedelta(days=5, hours=8), "Comfort"),
        # Sunday 23:59, last minute of the week (last entry 10050 is Night).
        (MONDAY + timedelta(days=6, hours=23, minutes=59), "Night"),
    ],
)
async def test_get_active_schedule_zone(async_home, at, expected):
    """A naive time is read as home local time against the fixture timetable."""
    zone = async_home.get_active_schedule_zone(at)
    assert zone is not None
    assert zone.name == expected


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        # Summer time (UTC+2): 04:30 UTC is 06:30 local, Comfort. Read as UTC
        # it would still be Night.
        (datetime(2026, 10, 19, 4, 30, tzinfo=UTC), "Comfort"),
        # Winter time (UTC+1), the day after the change: 05:30 UTC is 06:30
        # local, Comfort; 05:59 UTC is 06:59 local, still Comfort.
        (datetime(2026, 10, 26, 5, 30, tzinfo=UTC), "Comfort"),
        (datetime(2026, 10, 26, 5, 59, tzinfo=UTC), "Comfort"),
        (datetime(2026, 10, 26, 6, 0, tzinfo=UTC), "Eco"),
        # Sunday 22:59 UTC is Monday 00:00 local: the week starts over.
        (datetime(2026, 10, 25, 23, 0, tzinfo=UTC), "Night"),
        # Any aware time is converted, not only UTC: 07:30+02:00 is 06:30 CET.
        (datetime(2026, 10, 26, 7, 30, tzinfo=timezone(timedelta(hours=2))), "Comfort"),
    ],
)
async def test_get_active_schedule_zone_aware_time(async_home, at, expected):
    """An aware time is converted to home local time, across DST changes."""
    zone = async_home.get_active_schedule_zone(at)
    assert zone is not None
    assert zone.name == expected


async def test_get_active_schedule_zone_defaults_to_now(async_home):
    """Without a time, the current time is used."""
    with time_machine.travel(datetime(2026, 10, 26, 5, 30, tzinfo=UTC), tick=False):
        zone = async_home.get_active_schedule_zone()
    assert zone is not None
    assert zone.name == "Comfort"


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        # Before the first entry of the week: the last entry still applies.
        (MONDAY, "Night"),
        (MONDAY + timedelta(hours=6, minutes=59), "Night"),
        (MONDAY + timedelta(hours=7), "Comfort"),
        (MONDAY + timedelta(hours=21, minutes=59), "Comfort"),
        (MONDAY + timedelta(hours=22), "Night"),
        (MONDAY + timedelta(days=6, hours=23, minutes=59), "Night"),
    ],
)
async def test_get_active_schedule_zone_wraps_around_week(async_auth, at, expected):
    """The timetable repeats weekly and need not start at Monday 00:00."""
    # Deliberately unsorted, as nothing in the API guarantees the order.
    home = _home(
        async_auth, [{"zone_id": 1, "m_offset": 1320}, {"zone_id": 0, "m_offset": 420}]
    )
    zone = home.get_active_schedule_zone(at)
    assert zone is not None
    assert zone.name == expected


async def test_get_active_schedule_zone_string_zone_ids(async_auth):
    """Zone ids match whether the API sends them as numbers or strings."""
    home = _home(
        async_auth,
        [{"zone_id": "1", "m_offset": 0}, {"zone_id": 0, "m_offset": 420}],
        zones=[
            {"id": "0", "name": "Comfort", "type": 0, "rooms": []},
            {"id": 1, "name": "Night", "type": 1, "rooms": []},
        ],
    )
    assert home.get_active_schedule_zone(MONDAY).name == "Night"
    assert home.get_active_schedule_zone(MONDAY + timedelta(hours=8)).name == "Comfort"


@pytest.mark.parametrize(
    "timetable",
    [
        pytest.param([], id="empty"),
        pytest.param([{"zone_id": 0, "m_offset": None}], id="no_offset"),
        pytest.param([{"zone_id": 7, "m_offset": 0}], id="unknown_zone"),
        pytest.param([{"zone_id": None, "m_offset": 0}], id="no_zone_id"),
    ],
)
async def test_get_active_schedule_zone_unusable_timetable(async_auth, timetable):
    """A timetable that cannot resolve to a zone gives no zone and no setpoint."""
    home = _home(async_auth, timetable)
    assert home.get_active_schedule_zone(MONDAY) is None
    assert home.get_scheduled_temperature("1", MONDAY) is None


async def test_get_active_schedule_zone_skips_entries_without_offset(async_auth):
    """Entries without an offset are ignored, the others still apply."""
    home = _home(
        async_auth,
        [{"zone_id": 0, "m_offset": None}, {"zone_id": 1, "m_offset": 0}],
    )
    assert home.get_active_schedule_zone(MONDAY + timedelta(hours=12)).name == "Night"


async def test_get_active_schedule_zone_no_selected_schedule(async_home):
    """Without a selected schedule for the current mode, there is no zone."""
    async_home.temperature_control_mode = TemperatureControlMode.AUTO
    assert async_home.get_selected_schedule() is None
    assert async_home.get_active_schedule_zone(MONDAY) is None
    assert async_home.get_scheduled_temperature(ROOM_ID, MONDAY) is None


async def test_get_active_schedule_zone_no_timezone(async_auth):
    """A home without a time zone is read in UTC."""
    home = _home(
        async_auth,
        [{"zone_id": 1, "m_offset": 0}, {"zone_id": 0, "m_offset": 420}],
        timezone_name=None,
    )
    # 07:30 in Paris is 06:30 UTC, still Night in UTC.
    at = datetime(2026, 10, 26, 7, 30, tzinfo=timezone(timedelta(hours=1)))
    assert home.get_local_timezone() is UTC
    assert home.get_active_schedule_zone(at).name == "Night"


async def test_get_active_schedule_zone_unknown_timezone(async_auth, caplog):
    """An unknown time zone falls back to UTC with a warning."""
    home = _home(
        async_auth,
        [{"zone_id": 1, "m_offset": 0}, {"zone_id": 0, "m_offset": 420}],
        timezone_name="Mars/Olympus_Mons",
    )
    with caplog.at_level(logging.WARNING):
        assert home.get_local_timezone() is UTC
    assert "Unknown time zone Mars/Olympus_Mons for home schedule-home" in caplog.text
    assert home.get_active_schedule_zone(MONDAY + timedelta(hours=8)).name == "Comfort"


async def test_get_active_schedule_zone_malformed_timezone(async_auth, caplog):
    """A time zone that is not a string falls back to UTC with a warning."""
    home = _home(
        async_auth,
        [{"zone_id": 1, "m_offset": 0}, {"zone_id": 0, "m_offset": 420}],
    )
    home.timezone = 3600
    with caplog.at_level(logging.WARNING):
        assert home.get_local_timezone() is UTC
    assert "Unknown time zone 3600 for home schedule-home" in caplog.text
    assert home.get_active_schedule_zone(MONDAY + timedelta(hours=8)).name == "Comfort"


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        (MONDAY, 17),
        (MONDAY + timedelta(hours=6), 21),
        (MONDAY + timedelta(hours=7), 18),
    ],
)
async def test_get_scheduled_temperature(async_home, at, expected):
    """The setpoint is the one the active zone sets for the room."""
    assert async_home.get_scheduled_temperature(ROOM_ID, at) == expected


async def test_get_scheduled_temperature_room_not_in_zone(async_home):
    """A room the active zone does not list has no scheduled setpoint."""
    assert async_home.get_scheduled_temperature("unknown-room", MONDAY) is None


async def test_get_scheduled_temperature_defaults_to_now(async_home):
    """Without a time, the current time is used."""
    with time_machine.travel(datetime(2026, 10, 26, 6, 0, tzinfo=UTC), tick=False):
        assert async_home.get_scheduled_temperature(ROOM_ID) == 18


@pytest.mark.parametrize(
    ("room", "expected"),
    [
        pytest.param({"id": "1", "cooling_setpoint_temperature": 26}, 26, id="cooling"),
        pytest.param(
            {
                "id": "1",
                "therm_setpoint_temperature": 0,
                "cooling_setpoint_temperature": 26,
            },
            0,
            id="zero_is_a_setpoint",
        ),
        pytest.param({"id": "1"}, None, id="no_setpoint"),
        pytest.param({"id": 1, "therm_setpoint_temperature": 19}, 19, id="numeric_id"),
    ],
)
async def test_get_scheduled_temperature_setpoint_kinds(async_auth, room, expected):
    """Heating setpoints win, cooling ones are used otherwise, 0 is kept."""
    home = _home(
        async_auth,
        [{"zone_id": 0, "m_offset": 0}],
        zones=[{"id": 0, "name": "Comfort", "type": 0, "rooms": [room]}],
    )
    assert home.get_scheduled_temperature("1", MONDAY) == expected


@pytest.mark.parametrize(
    ("zone", "expected"),
    [
        pytest.param(
            {"rooms_temp": [{"room_id": "1", "temp": 18.5}]}, 18.5, id="rooms_temp_only"
        ),
        pytest.param(
            {
                "rooms": [{"id": "1", "therm_setpoint_temperature": 19}],
                "rooms_temp": [{"room_id": "1", "temp": 18.5}],
            },
            19,
            id="rooms_win",
        ),
        pytest.param(
            {
                "rooms": [{"id": "1", "therm_setpoint_mode": "off"}],
                "rooms_temp": [{"room_id": "1", "therm_setpoint_mode": "off"}],
            },
            None,
            id="room_off",
        ),
        pytest.param({"rooms_temp": [{"temp": 18.5}]}, None, id="no_room_id"),
        pytest.param(
            {"rooms_temp": [{"room_id": 1, "temp": 18.5}]}, 18.5, id="numeric_room_id"
        ),
        pytest.param({"rooms_temp": None}, None, id="rooms_temp_null"),
        pytest.param(
            {"rooms_temp": ["1", None, {"room_id": "1", "temp": 18.5}]},
            18.5,
            id="rooms_temp_malformed_entries",
        ),
    ],
)
async def test_get_scheduled_temperature_rooms_temp(async_auth, zone, expected):
    """Setpoints listed only in `rooms_temp` are used as a fallback."""
    home = _home(
        async_auth,
        [{"zone_id": 0, "m_offset": 0}],
        zones=[{"id": 0, "name": "Comfort", "type": 0, **zone}],
    )
    assert home.get_scheduled_temperature("1", MONDAY) == expected


@pytest.mark.parametrize(
    ("mode", "at", "zone_name", "room_id", "expected"),
    [
        # Heating schedule 1: Zone 1 from Monday 00:00, Zone 0 from 07:30.
        (TemperatureControlMode.HEATING, MONDAY, "Zone 1", "ac_room_bedroom_2", 15),
        (
            TemperatureControlMode.HEATING,
            MONDAY + timedelta(hours=7, minutes=30),
            "Zone 0",
            "ac_room_bedroom_2",
            17,
        ),
        # The living room is off in heating zones: no setpoint.
        (TemperatureControlMode.HEATING, MONDAY, "Zone 1", "ac_room_living", None),
        # Cooling schedule 3: Zone 2 from Monday 08:00, room off.
        (
            TemperatureControlMode.COOLING,
            MONDAY + timedelta(hours=8),
            "Zone 2",
            "ac_room_living",
            None,
        ),
    ],
)
async def test_get_active_schedule_zone_captured_home(
    async_home_ac, mode, at, zone_name, room_id, expected
):
    """The zone follows the schedule selected for the current mode."""
    async_home_ac.temperature_control_mode = mode
    assert async_home_ac.get_active_schedule_zone(at).name == zone_name
    assert async_home_ac.get_scheduled_temperature(room_id, at) == expected
