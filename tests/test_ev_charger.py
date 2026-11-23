"""Define tests for EV charging station modules."""

from unittest.mock import AsyncMock, patch

import pytest

import pyatmo
from pyatmo import DeviceType
from pyatmo.modules.device_types import ChargingStationStatus, DeviceCategory
from pyatmo.modules.module import MeasureInterval


async def test_nlevse_payload_parsing(async_auth):
    """Test Legrand electric vehicle charging station (NLEVSE) module parsing."""
    home = pyatmo.Home(
        async_auth,
        {
            "id": "home_evse",
            "modules": [
                {
                    "id": "12:34:56:00:00:99",
                    "type": "NLEVSE",
                    "name": "Green'Up Charger",
                    "bridge": "12:34:56:aa:00:01",
                },
            ],
        },
    )

    module = home.modules["12:34:56:00:00:99"]
    assert module.device_type == DeviceType.NLEVSE
    assert module.device_category == DeviceCategory.ev_charger
    assert module.name == "Green'Up Charger"
    assert module.bridge == "12:34:56:aa:00:01"
    assert module.charging_station_status is None
    assert module.power is None
    assert module.reachable is None

    await module.update(
        {
            "id": "12:34:56:00:00:99",
            "type": "NLEVSE",
            "firmware_revision": 94,
            "wifi_strength": 71,
            "charging_station_status": 2,
            "charging_station_error": 0,
            "current_charge_duration": 120,
            "current_charge_instant_consumption": 3700,
            "current_total_charge_consumption": 7400,
            "rs485_link_state": True,
            "tic_link_state": True,
            "hardware_version": 2,
            "connection": "connected",
            "sequence_id": 42,
            "reachable": True,
        },
    )

    assert module.firmware_revision == 94
    assert module.wifi_strength == 71
    assert module.charging_station_status == ChargingStationStatus.charging
    assert module.charging_station_error == 0
    assert module.current_charge_duration == 120
    assert module.current_charge_instant_consumption == 3700
    assert module.current_total_charge_consumption == 7400
    assert module.power == 3700
    assert module.rs485_link_state is True
    assert module.tic_link_state is True
    assert module.hardware_version == 2
    assert module.connection == "connected"
    assert module.sequence_id == 42
    assert module.reachable is True

    assert "power" in module.features
    assert "charging_station_status" in module.features
    assert "current_charge_instant_consumption" in module.features
    assert "current_total_charge_consumption" in module.features
    assert "reachable" in module.features


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        (0, ChargingStationStatus.available),
        (1, ChargingStationStatus.waiting),
        (2, ChargingStationStatus.charging),
        (3, ChargingStationStatus.finished),
        (4, ChargingStationStatus.error),
        ("available", ChargingStationStatus.available),
        ("charging", ChargingStationStatus.charging),
        (99, ChargingStationStatus.unknown),
        ("unexpected_status", ChargingStationStatus.unknown),
    ],
)
async def test_nlevse_charging_station_status(async_auth, raw_status, expected):
    """Test mapping of raw charging_station_status values to ChargingStationStatus enum."""
    home = pyatmo.Home(
        async_auth,
        {
            "id": "home_evse",
            "modules": [{"id": "evse_1", "type": "NLEVSE"}],
        },
    )
    module = home.modules["evse_1"]

    await module.update(
        {
            "id": "evse_1",
            "type": "NLEVSE",
            "charging_station_status": raw_status,
        },
    )

    assert module.charging_station_status == expected


async def test_nlevse_power_fallback(async_auth):
    """Test power attribute resolution: explicit power takes precedence over instantaneous consumption."""
    home = pyatmo.Home(
        async_auth,
        {
            "id": "home_evse",
            "modules": [{"id": "evse_1", "type": "NLEVSE"}],
        },
    )
    module = home.modules["evse_1"]

    # When power is not provided, current_charge_instant_consumption is used
    await module.update(
        {
            "id": "evse_1",
            "type": "NLEVSE",
            "current_charge_instant_consumption": 3700,
        },
    )
    assert module.power == 3700

    # When power is explicitly provided, it takes precedence
    await module.update(
        {
            "id": "evse_1",
            "type": "NLEVSE",
            "power": 4500,
            "current_charge_instant_consumption": 3700,
        },
    )
    assert module.power == 4500


async def test_nlevse_energy_history_retrieval(async_auth):
    """Test energy history retrieval on an NLEVSE charging station."""
    home = pyatmo.Home(
        async_auth,
        {
            "id": "home_evse",
            "modules": [{"id": "evse_1", "type": "NLEVSE", "bridge": "bridge_1"}],
        },
    )
    module = home.modules["evse_1"]

    mock_body = [
        {
            "beg_time": 1700000000 + 1800,
            "step_time": 3600,
            "value": [
                [None, 3500, None, None],
                [None, 3600, None, None],
            ],
        },
    ]

    with patch.object(
        module,
        "_energy_api_calls",
        AsyncMock(return_value=("energy_filters", mock_body)),
    ):
        await module.async_update_measures(
            start_time=1700000000,
            end_time=1700007200,
            interval=MeasureInterval.HOUR,
        )

    assert len(module.historical_data) == 2
    assert module.sum_energy_elec == 7100
    assert module.historical_data[0]["Wh"] == 3500
    assert module.historical_data[1]["Wh"] == 3600
