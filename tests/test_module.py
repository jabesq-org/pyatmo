"""Define tests for the module base helpers."""

import pytest

from pyatmo.modules.module import process_battery_state


@pytest.mark.parametrize(
    ("battery_state", "expected"),
    [
        ("max", 100),
        ("full", 90),
        ("high", 75),
        ("medium", 50),
        ("low", 25),
        ("very_low", 10),
    ],
)
def test_process_battery_state_known_values(battery_state: str, expected: int) -> None:
    """Known battery states map to their percent value."""

    assert process_battery_state(battery_state) == expected


def test_process_battery_state_unknown_value_returns_zero() -> None:
    """An unknown battery state degrades gracefully to 0 instead of raising."""

    assert process_battery_state("empty") == 0
