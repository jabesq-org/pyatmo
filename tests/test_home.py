"""Define tests for home module."""

import json
import logging
from unittest.mock import AsyncMock, patch

import anyio
import pytest

import pyatmo
from pyatmo import DeviceType, InvalidScheduleError, NoDeviceError, NoScheduleError
from pyatmo.enums import (
    SCHEDULE_TYPE_MAPPING,
    PressureUnit,
    ScheduleType,
    TemperatureControlMode,
    UnitSystem,
    WindUnit,
)
from pyatmo.home import Home, get_temperature_control_mode
from pyatmo.modules.device_types import DeviceCategory
from tests.common import MockResponse, load_fixture


async def test_async_home(async_home):
    """Test basic home setup."""
    room_id = "3688132631"
    room = async_home.rooms[room_id]
    assert room.device_types == {
        DeviceType.NDB,
        DeviceType.NACamera,
        DeviceType.NBR,
        DeviceType.NIS,
        DeviceType.NBO,
        DeviceType.NPC,
        DeviceType.NLPD,
    }
    assert len(async_home.rooms) == 9
    assert len(async_home.modules) == 51
    assert async_home.modules != room.modules

    module_id = "12:34:56:10:f1:66"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NDB

    module_id = "12:34:56:10:b9:0e"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NOC

    assert async_home.temperature_control_mode == "cooling"


async def test_async_home_set_schedule(async_home):
    """Test home schedule."""
    schedule_id = "591b54a2764ff4d50d8b5795"
    selected_schedule = async_home.get_selected_schedule()
    assert selected_schedule.entity_id == schedule_id
    assert async_home.is_valid_schedule(schedule_id)
    assert not async_home.is_valid_schedule("123")
    assert async_home.get_hg_temp() == 7
    assert async_home.get_away_temp() == 14


async def test_async_set_schedule_temperatures(async_home):
    """Test setting schedule temperatures."""
    schedule_id = "591b54a2764ff4d50d8b5795"
    schedule = async_home.get_selected_schedule()

    assert schedule.entity_id == schedule_id
    zone = next((zone for zone in schedule.zones if zone.entity_id == 1), None)
    assert zone is not None
    room = next((room for room in zone.rooms if room.entity_id == "2746182631"), None)
    assert room is not None
    assert room.therm_setpoint_temperature == 17

    temps = {"2746182631": 15}

    async with await anyio.open_file(
        "fixtures/sync_schedule_591b54a2764ff4d50d8b5795.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.loads(await fixture_file.read())

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse({"status": "ok"}, 200)),
    ) as mock_resp:
        await async_home.async_set_schedule_temperatures(1, temps)

        mock_resp.assert_awaited_with(
            endpoint="api/synchomeschedule",
            params={
                "params": {
                    "home_id": "91763b24c43d3e344f424e8b",
                    "schedule_id": schedule_id,
                    "name": "Default",
                },
                "json": json_fixture,
            },
        )


async def test_async_sync_schedule(async_home):
    """Test setting schedule temperatures."""
    schedule_id = "b1b54a2f45795764f59d50d8"
    schedule = async_home.schedules.get(schedule_id)

    assert schedule is not None
    assert schedule.entity_id == schedule_id
    zone = next((zone for zone in schedule.zones if zone.entity_id == 1), None)
    assert zone is not None
    room = next((room for room in zone.rooms if room.entity_id == "2746182631"), None)
    assert room is not None
    assert room.therm_setpoint_temperature == 17

    # set a new room temperature
    room.therm_setpoint_temperature = 14

    async with await anyio.open_file(
        "fixtures/sync_schedule_b1b54a2f45795764f59d50d8.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.loads(await fixture_file.read())

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse({"status": "ok"}, 200)),
    ) as mock_resp:
        await async_home.async_sync_schedule(schedule)

        mock_resp.assert_awaited_with(
            endpoint="api/synchomeschedule",
            params={
                "params": {
                    "home_id": "91763b24c43d3e344f424e8b",
                    "schedule_id": schedule_id,
                    "name": "Default",
                },
                "json": json_fixture,
            },
        )


async def test_async_sync_schedule_invalid_schedule(async_home):
    """Test syncing an invalid schedule."""
    invalid_schedule = {"invalid": "data"}

    with (
        pytest.raises(InvalidScheduleError),
        patch(
            "pyatmo.home.is_valid_schedule",
            return_value=False,
        ),
    ):
        await async_home.async_sync_schedule(invalid_schedule)


async def test_async_home_data_no_body(async_auth):
    """Test home data with no body."""
    async with await anyio.open_file(
        "fixtures/homesdata_empty.json",
        encoding="utf-8",
    ) as fixture_file:
        json_fixture = json.loads(await fixture_file.read())

    mock_request = AsyncMock(return_value=MockResponse(json_fixture, 200))
    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        mock_request,
    ):
        climate = pyatmo.AsyncAccount(async_auth)
        with pytest.raises(NoDeviceError):
            await climate.async_update_topology()
        mock_request.assert_awaited_once()


async def test_async_set_persons_home(async_account):
    """Test marking a person being at home."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]

    person_ids = [
        "91827374-7e04-5298-83ad-a0cb8372dff1",
        "91827375-7e04-5298-83ae-a0cb8372dff2",
    ]

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        await home.async_set_persons_home(person_ids)

        mock_resp.assert_awaited_with(
            params={"home_id": home_id, "person_ids[]": person_ids},
            endpoint="api/setpersonshome",
        )


async def test_async_set_persons_away(async_account):
    """Test marking a set of persons being away."""
    home_id = "91763b24c43d3e344f424e8b"
    home = async_account.homes[home_id]

    async with await anyio.open_file(
        "fixtures/status_ok.json",
        encoding="utf-8",
    ) as json_file:
        response = json.loads(await json_file.read())

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(response, 200)),
    ) as mock_resp:
        person_id = "91827374-7e04-5298-83ad-a0cb8372dff1"
        await home.async_set_persons_away(person_id)

        mock_resp.assert_awaited_with(
            params={"home_id": home_id, "person_id": person_id},
            endpoint="api/setpersonsaway",
        )

        await home.async_set_persons_away()

        mock_resp.assert_awaited_with(
            params={"home_id": home_id},
            endpoint="api/setpersonsaway",
        )


async def test_home_event_update(async_account):
    """Test basic event update."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_events(home_id=home_id)
    home = async_account.homes[home_id]

    events = home.events
    assert len(events) == 8

    module_id = "12:34:56:10:b9:0e"
    assert module_id in home.modules
    module = home.modules[module_id]

    events = module.events
    assert len(events) == 5
    assert events[0].event_type == "outdoor"
    assert events[0].video_id == "11111111-2222-3333-4444-b42f0fc4cfad"
    assert events[1].event_type == "connection"


async def test_async_home_module_error_code(async_account):
    """Test that per-module error code from homestatus errors[] is surfaced."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    home = async_account.homes[home_id]

    module_id = "12:34:56:00:fa:d0"
    assert module_id in home.modules
    module = home.modules[module_id]

    async with await anyio.open_file(
        "fixtures/home_status_error_disconnected.json",
        encoding="utf-8",
    ) as json_file:
        home_status_fixture = json.loads(await json_file.read())
    mock_home_status_resp = MockResponse(home_status_fixture, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=mock_home_status_resp),
    ) as mock_request:
        await async_account.async_update_status(home_id)
        mock_request.assert_called()

    assert module.error_code == 6
    assert "error_code" not in module.features
    # The errored module and its bridged children are unreachable.
    assert module.reachable is False
    assert home.modules["12:34:56:00:01:ae"].reachable is False

    # Recovery: a subsequent healthy /homestatus update (the module is reported
    # in home.modules again) must clear the stale error code back to None.
    await async_account.async_update_status(home_id)
    assert module.error_code is None


async def test_async_home_module_setup_date(async_home):
    """Test that module setup_date from /homesdata topology is surfaced."""
    module_id = "12:34:56:00:fa:d0"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.setup_date == 1494963356
    assert "setup_date" not in module.features


async def test_async_home_room_type_and_therm_relay(async_home):
    """Test room type + therm_relay from /homesdata topology are surfaced."""
    livingroom = async_home.rooms["2746182631"]
    assert livingroom.room_type == "livingroom"

    bureau = async_home.rooms["222452125"]
    assert bureau.room_type == "electrical_cabinet"
    assert bureau.therm_relay == "12:34:56:20:f5:44"

    # Rooms without therm_relay in the payload default to None.
    assert livingroom.therm_relay is None


async def test_async_account_user_country_and_consent(async_account):
    """Test user country + pending_user_consent from /homesdata are surfaced."""
    assert async_account.user == "john@doe.com"
    assert async_account.user_country == "DE"
    assert async_account.pending_user_consent is True

    # The raw user block (email/id PII) must not leak into raw_data, which
    # consumers such as Home Assistant diagnostics serialize wholesale.
    assert "user" not in async_account.raw_data


async def test_async_home_electricity_schedule(async_home):
    """Test electricity schedule tariff fields + zone prices are parsed."""
    schedule = async_home.schedules["c1c54a2f45795764f59d50d9"]
    assert schedule.type == "electricity"
    assert schedule.tariff == "custom"
    assert schedule.tariff_option == "peak_and_off_peak"
    assert schedule.power_threshold == 6
    assert schedule.contract_power_unit == "kVA"

    peak = next(z for z in schedule.zones if z.entity_id == 0)
    assert peak.price_type == "peak"
    assert peak.price_value == 0.21
    off_peak = next(z for z in schedule.zones if z.entity_id == 1)
    assert off_peak.price_type == "off_peak"
    assert off_peak.price_value == 0.16


async def test_async_home_event_schedule(async_home):
    """Test event schedule twilight timetables + zone module actions are parsed."""
    schedule = async_home.schedules["d1d54a2f45795764f59d50da"]
    assert schedule.type == "event"

    assert len(schedule.timetable_sunrise) == 1
    sunrise = schedule.timetable_sunrise[0]
    assert sunrise.zone_id == 0
    assert sunrise.day == 1
    assert sunrise.twilight_offset == -30

    assert len(schedule.timetable_sunset) == 1
    assert schedule.timetable_sunset[0].twilight_offset == 15

    morning = next(z for z in schedule.zones if z.entity_id == 0)
    assert len(morning.modules) == 1
    light = morning.modules[0]
    assert light.entity_id == "12:34:56:00:01:ae"
    assert light.bridge == "12:34:56:00:fa:d0"
    assert light.on is True
    assert light.brightness == 80

    evening = next(z for z in schedule.zones if z.entity_id == 1)
    shutter = evening.modules[0]
    assert shutter.target_position == 100
    assert shutter.fan_speed == 2


def test_device_types_missing():
    """Test handling of missing device types."""

    assert DeviceType("NOC") == DeviceType.NOC
    assert DeviceType("UNKNOWN") == DeviceType.NLunknown


async def test_module_bridged_key_variants(async_home):
    """Both `modules_bridged` and `module_bridged` populate Module.modules."""
    plural = async_home.get_module(
        {"id": "aa:aa", "type": "NLP", "modules_bridged": ["child-1"]},
    )
    assert plural.modules == ["child-1"]

    singular = async_home.get_module(
        {"id": "bb:bb", "type": "NLP", "module_bridged": ["child-2"]},
    )
    assert singular.modules == ["child-2"]


async def test_module_bridged_key_precedence(async_home):
    """When both keys are present, `modules_bridged` wins over `module_bridged`."""
    mod = async_home.get_module(
        {
            "id": "ee:ee",
            "type": "NLP",
            "modules_bridged": ["canonical"],
            "module_bridged": ["alias"],
        },
    )
    assert mod.modules == ["canonical"]


async def test_module_bridged_key_topology_update(async_home):
    """Both bridged-key spellings work on the update_topology reflection path."""
    # update_topology -> _update_attributes drives the NETATMO_ATTRIBUTES_MAP
    # "modules" entry (bridged_module_ids), a different code path than
    # Module.__init__.
    plural = async_home.get_module({"id": "cc:cc", "type": "NLP"})
    plural.update_topology(
        {"id": "cc:cc", "type": "NLP", "modules_bridged": ["child-3"]},
    )
    assert plural.modules == ["child-3"]

    singular = async_home.get_module({"id": "dd:dd", "type": "NLP"})
    singular.update_topology(
        {"id": "dd:dd", "type": "NLP", "module_bridged": ["child-4"]},
    )
    assert singular.modules == ["child-4"]


async def test_home_geolocation(async_home):
    """Test home geolocation fields from /homesdata topology are surfaced."""
    assert async_home.altitude == 112
    assert async_home.country == "DE"
    assert async_home.timezone == "Europe/Berlin"
    # Coordinates are exposed as-is; the API's lat/lon ordering is ambiguous
    # across schema variants, so the library does not reinterpret them.
    assert async_home.coordinates == [52.516263, 13.377726]


async def test_home_geolocation_topology_update(async_home):
    """Geolocation is refreshed on the update_topology path, not only __init__."""
    async_home.update_topology(
        {
            "id": async_home.entity_id,
            "name": "MYHOME",
            "altitude": 5,
            "coordinates": [1.0, 2.0],
            "country": "FR",
            "timezone": "Europe/Paris",
        },
    )
    assert async_home.altitude == 5
    assert async_home.coordinates == [1.0, 2.0]
    assert async_home.country == "FR"
    assert async_home.timezone == "Europe/Paris"


async def test_home_geolocation_partial_update_preserves(async_home):
    """A partial topology update must not wipe known geolocation.

    Home.update calls update_topology({"modules": [...]}) for newly-seen
    modules; that payload omits the geolocation keys and must keep the
    values already populated from /homesdata.
    """
    assert async_home.altitude == 112
    assert async_home.coordinates == [52.516263, 13.377726]

    async_home.update_topology({"modules": []})

    assert async_home.altitude == 112
    assert async_home.coordinates == [52.516263, 13.377726]
    assert async_home.country == "DE"
    assert async_home.timezone == "Europe/Berlin"


async def test_home_update_new_module_preserves_home_fields(async_home):
    """Discovering a new module via /homestatus must not wipe home fields.

    Home.update registers a not-yet-seen module; that path must not reset
    name/therm state/geolocation, whose keys are absent from /homestatus.
    """
    name = async_home.name
    altitude = async_home.altitude
    coordinates = async_home.coordinates
    therm_mode = async_home.therm_mode
    assert name == "MYHOME"

    # Capture the pre-existing modules: routing a single-module payload through
    # update_topology used to pop every other module via its removal loop.
    existing_module_ids = set(async_home.modules)
    assert len(existing_module_ids) > 1

    new_module = {"id": "ff:ff:ff:ff:ff:ff", "type": "NAMain"}
    assert new_module["id"] not in async_home.modules

    await async_home.update(
        {"home": {"id": async_home.entity_id, "modules": [new_module]}},
    )

    assert new_module["id"] in async_home.modules
    assert existing_module_ids <= set(async_home.modules)
    assert async_home.name == name
    assert async_home.altitude == altitude
    assert async_home.coordinates == coordinates
    assert async_home.therm_mode == therm_mode


async def test_account_user_units(async_account):
    """Test user display-unit preferences from /homesdata are surfaced."""
    assert async_account.unit_system == UnitSystem.METRIC
    assert async_account.unit_wind == WindUnit.MPH
    assert async_account.unit_pressure == PressureUnit.MMHG

    # The raw user block (email/id PII) must not leak into raw_data.
    assert "user" not in async_account.raw_data


async def test_account_user_units_missing(async_auth):
    """Test unit preferences stay None when the keys are absent."""
    account = pyatmo.AsyncAccount(async_auth)

    async def fake_request(*_, **__):
        body = {"body": {"homes": [{"id": "1", "name": "home"}], "user": {}}}
        return MockResponse(body, 200)

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        fake_request,
    ):
        await account.async_update_topology()

    assert account.unit_system is None
    assert account.unit_wind is None
    assert account.unit_pressure is None


def test_account_user_units_unknown_fallback(caplog):
    """Test out-of-range unit codes fall back to UNKNOWN and log a warning."""
    assert UnitSystem(99) is UnitSystem.UNKNOWN
    assert WindUnit(99) is WindUnit.UNKNOWN
    assert PressureUnit(99) is PressureUnit.UNKNOWN
    assert "unknown" in caplog.text.lower()


async def test_device_type_aliases(async_home):
    """Legacy/typo module types from /homesdata resolve to canonical classes."""
    # `NBD` is a transposition of the canonical `NDB` (Smart Video Doorbell).
    doorbell = async_home.get_module({"id": "1", "type": "NBD"})
    assert isinstance(doorbell, pyatmo.modules.NDB)
    assert doorbell.device_type == DeviceType.NDB

    # `NADoorTag` is a legacy alias of `NACamDoorTag`.
    doortag = async_home.get_module({"id": "2", "type": "NADoorTag"})
    assert isinstance(doortag, pyatmo.modules.NACamDoorTag)
    assert doortag.device_type == DeviceType.NACamDoorTag


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("heating", TemperatureControlMode.HEATING),
        ("cooling", TemperatureControlMode.COOLING),
        ("auto", TemperatureControlMode.AUTO),
        (None, None),
    ],
)
def test_get_temperature_control_mode(raw_value, expected):
    """Known modes parse to their enum member; missing value stays None."""
    assert get_temperature_control_mode(raw_value) == expected


def test_get_temperature_control_mode_unknown(caplog):
    """Unknown mode degrades to None with a warning, does not raise."""
    with caplog.at_level(logging.WARNING):
        assert get_temperature_control_mode("garbage") is None
    assert "garbage" in caplog.text


def test_schedule_type_mapping_covers_all_modes():
    """Every TemperatureControlMode maps to a ScheduleType (no KeyError path)."""
    for mode in TemperatureControlMode:
        assert mode in SCHEDULE_TYPE_MAPPING
    assert SCHEDULE_TYPE_MAPPING[TemperatureControlMode.AUTO] == ScheduleType.AUTO


async def test_schedule_lookup_auto_mode_no_keyerror(async_home):
    """Home in auto mode: schedule lookups must not raise KeyError."""
    async_home.temperature_control_mode = TemperatureControlMode.AUTO
    # No auto schedule in the fixture -> no match, but must not crash.
    assert async_home.get_selected_schedule() is None
    assert async_home.get_available_schedules() == []


async def test_home_init_auto_mode_parses_and_selects_schedule(async_auth):
    """Home built from a tcm='auto' payload must not raise (issue #176631).

    Reproduces the original crash path (Home.__init__ ->
    get_temperature_control_mode) with a real raw payload rather than a
    mutated fixture, and confirms an auto-typed schedule is selectable.
    """
    raw_data = {
        "id": "auto-home",
        "name": "Auto Home",
        "temperature_control_mode": "auto",
        "schedules": [
            {
                "id": "sched-auto",
                "name": "Auto schedule",
                "type": "auto",
                "selected": True,
                "hg_temp": 7,
                "away_temp": 14,
            },
            {
                "id": "sched-therm",
                "name": "Therm schedule",
                "type": "therm",
                "selected": False,
            },
        ],
    }

    home = Home(async_auth, raw_data)

    assert home.temperature_control_mode == TemperatureControlMode.AUTO
    selected = home.get_selected_schedule()
    assert selected is not None
    assert selected.entity_id == "sched-auto"
    assert home.get_hg_temp() == 7
    assert home.get_away_temp() == 14
    assert [s.entity_id for s in home.get_available_schedules()] == ["sched-auto"]


def _schedule_home_raw(schedules: list[dict], mode: str | None = "heating") -> dict:
    """Return a minimal /homesdata home payload carrying the given schedules."""
    raw_data: dict = {
        "id": "schedule-home",
        "name": "Schedule Home",
        "schedules": schedules,
    }
    if mode is not None:
        raw_data["temperature_control_mode"] = mode
    return raw_data


# A therm schedule pair plus a cooling schedule, so type scoping is observable.
SCHEDULE_A = {"id": "sched-a", "name": "Winter", "type": "therm", "selected": True}
SCHEDULE_B = {"id": "sched-b", "name": "Summer", "type": "therm"}
SCHEDULE_COOL = {
    "id": "sched-cool",
    "name": "Summer",
    "type": "cooling",
    "selected": True,
}


async def test_schedule_update_topology_absent_selected_is_not_selected(async_auth):
    """An omitted "selected" key means not selected, it must not stay sticky.

    /homesdata only carries "selected" on the currently selected schedule, so
    keeping the previous value made a once-selected schedule selected forever.
    """
    home = Home(async_auth, _schedule_home_raw([SCHEDULE_A]))
    schedule = home.schedules["sched-a"]
    assert schedule.selected is True

    schedule.update_topology({"id": "sched-a", "name": "Winter", "type": "therm"})

    assert schedule.selected is False


@pytest.mark.parametrize(
    "order",
    [
        # Dict insertion order follows the payload, and get_selected_schedule()
        # returns the first match, so the stale-flag bug is only visible when
        # the previously selected schedule is listed first.
        ["sched-a", "sched-b"],
        ["sched-b", "sched-a"],
    ],
)
async def test_home_update_topology_switches_selected_schedule(async_auth, order):
    """After a topology update only the newly selected schedule is selected."""
    home = Home(async_auth, _schedule_home_raw([SCHEDULE_A, SCHEDULE_B]))
    assert home.get_selected_schedule().entity_id == "sched-a"

    updated = {
        "sched-a": {"id": "sched-a", "name": "Winter", "type": "therm"},
        "sched-b": {
            "id": "sched-b",
            "name": "Summer",
            "type": "therm",
            "selected": True,
        },
    }
    home.update_topology(
        _schedule_home_raw([updated[schedule_id] for schedule_id in order]),
    )

    assert home.schedules["sched-a"].selected is False
    assert home.schedules["sched-b"].selected is True
    assert home.get_selected_schedule().entity_id == "sched-b"


async def test_async_switch_schedule_updates_selected_flags(async_auth):
    """A successful switch flips the flags of the switched schedule type only."""
    home = Home(
        async_auth,
        _schedule_home_raw([SCHEDULE_A, SCHEDULE_B, SCHEDULE_COOL]),
    )

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse({"status": "ok"}, 200)),
    ):
        assert await home.async_switch_schedule("sched-b") is True

    assert home.schedules["sched-b"].selected is True
    assert home.schedules["sched-a"].selected is False
    # Selection is tracked per type, the cooling schedule stays untouched.
    assert home.schedules["sched-cool"].selected is True


async def test_async_switch_schedule_error_keeps_selected_flags(async_auth):
    """A failed switch must leave the cache to the next topology update."""
    home = Home(async_auth, _schedule_home_raw([SCHEDULE_A, SCHEDULE_B]))

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse({"status": "error"}, 200)),
    ):
        assert await home.async_switch_schedule("sched-b") is False

    assert home.schedules["sched-a"].selected is True
    assert home.schedules["sched-b"].selected is False


async def test_async_switch_schedule_invalid_id_keeps_selected_flags(async_auth):
    """An unknown schedule id raises before anything is mutated."""
    home = Home(async_auth, _schedule_home_raw([SCHEDULE_A, SCHEDULE_B]))

    with pytest.raises(NoScheduleError):
        await home.async_switch_schedule("does-not-exist")

    assert home.schedules["sched-a"].selected is True
    assert home.schedules["sched-b"].selected is False


@pytest.mark.parametrize(
    ("mode", "name", "expected"),
    [
        ("heating", "Winter", "sched-a"),
        ("heating", "Summer", "sched-b"),
        # "Summer" exists as a therm and a cooling schedule: the lookup is
        # scoped to the active temperature control mode.
        ("cooling", "Summer", "sched-cool"),
        ("cooling", "Winter", None),
        ("heating", "Unknown", None),
        # Without a temperature control mode no schedule is selectable.
        (None, "Winter", None),
    ],
)
async def test_get_schedule_by_name(async_auth, mode, name, expected):
    """Only schedules of the active type are resolvable by name."""
    home = Home(
        async_auth,
        _schedule_home_raw([SCHEDULE_A, SCHEDULE_B, SCHEDULE_COOL], mode=mode),
    )

    schedule = home.get_schedule_by_name(name)

    assert (schedule.entity_id if schedule else None) == expected


@pytest.mark.parametrize(
    ("schedule_id", "expected_selected"),
    [
        # The cooling schedule keeps its flag either way: selection is tracked
        # per schedule type.
        ("sched-a", ["sched-a", "sched-cool"]),
        ("sched-b", ["sched-b", "sched-cool"]),
        ("sched-cool", ["sched-a", "sched-cool"]),
    ],
)
async def test_set_selected_schedule(async_auth, schedule_id, expected_selected):
    """Selecting a schedule locally only affects schedules of its type."""
    home = Home(
        async_auth,
        _schedule_home_raw([SCHEDULE_A, SCHEDULE_B, SCHEDULE_COOL]),
    )

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(),
    ) as mock_resp:
        home.set_selected_schedule(schedule_id)

    # The webhook path has nothing to POST, the switch already happened.
    mock_resp.assert_not_awaited()
    assert [
        sid for sid, schedule in home.schedules.items() if schedule.selected
    ] == expected_selected


async def test_set_selected_schedule_invalid_id(async_auth):
    """An unknown schedule id raises before anything is mutated."""
    home = Home(async_auth, _schedule_home_raw([SCHEDULE_A, SCHEDULE_B]))

    with pytest.raises(NoScheduleError):
        home.set_selected_schedule("does-not-exist")

    assert home.schedules["sched-a"].selected is True
    assert home.schedules["sched-b"].selected is False


async def test_async_home_module_reachable_feature(async_home):
    """The private reachability attribute stays out of the public feature set."""
    module = async_home.modules["12:34:56:00:01:ae"]
    assert "reachable" in module.features
    assert "_reachable" not in module.features


async def test_async_home_module_reachable_absent_key_preserved(async_account):
    """An absent `reachable` key keeps the previous value instead of forcing False."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_status(home_id)
    home = async_account.homes[home_id]

    module_id = "12:34:56:00:01:01:01:b6"
    module = home.modules[module_id]
    assert module.reachable is True

    homestatus = json.loads(load_fixture("homestatus_91763b24c43d3e344f424e8b.json"))
    for raw_module in homestatus["body"]["home"]["modules"]:
        if raw_module["id"] == module_id:
            del raw_module["reachable"]

    with patch(
        "pyatmo.auth.AbstractAsyncAuth.async_post_api_request",
        AsyncMock(return_value=MockResponse(homestatus, 200)),
    ):
        await async_account.async_update_status(home_id)

    assert module.reachable is True


async def test_home_with_modules_has_status(async_home):
    """A home carrying modules is pollable."""
    assert async_home.modules
    assert async_home.has_status is True


async def test_home_without_modules_has_no_status(async_home):
    """A home carrying no modules has nothing for /homestatus to report."""
    async_home.modules = {}

    assert async_home.has_status is False


async def test_weather_modules_do_not_disqualify_a_home(async_home):
    """Regression guard: /homestatus does report weather modules.

    Measured 2026-08-13 -- home 6a61e0986124db53ca0248fa holds NAMain and
    NAModule1, and its /homestatus returns all 7 modules including both. An
    earlier draft excluded the weather category and would have hidden it.
    """
    for module in async_home.modules.values():
        module.device_category = DeviceCategory.weather

    assert async_home.has_status is True


async def test_unmapped_module_keeps_the_home_pollable(async_home):
    """An unrecognised device type must never hide a home.

    DEVICE_CATEGORY_MAP.get() returns None for mapped types such as NLG and
    NAPlug, so a missing category cannot mean "not pollable".
    """
    for module in async_home.modules.values():
        module.device_category = None

    assert async_home.has_status is True
