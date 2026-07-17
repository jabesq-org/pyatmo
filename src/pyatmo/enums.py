"""Enums for the pyatmo package."""

from __future__ import annotations

from enum import IntEnum, StrEnum
import logging
from typing import Literal

LOG: logging.Logger = logging.getLogger(__name__)


class UnitSystem(IntEnum):
    """Measurement system reported in the /homesdata user block."""

    METRIC = 0
    IMPERIAL = 1
    unknown = -1

    @classmethod
    def _missing_(cls, key: object) -> Literal[UnitSystem.unknown]:
        """Handle unknown unit system values."""

        msg: str = f"{key} unit system is unknown"
        LOG.warning(msg)
        return UnitSystem.unknown


class WindUnit(IntEnum):
    """Wind-speed unit reported in the /homesdata user block."""

    KPH = 0
    MPH = 1
    MS = 2
    BEAUFORT = 3
    KNOT = 4
    unknown = -1

    @classmethod
    def _missing_(cls, key: object) -> Literal[WindUnit.unknown]:
        """Handle unknown wind unit values."""

        msg: str = f"{key} wind unit is unknown"
        LOG.warning(msg)
        return WindUnit.unknown


class PressureUnit(IntEnum):
    """Pressure unit reported in the /homesdata user block."""

    MBAR = 0
    INHG = 1
    MMHG = 2
    unknown = -1

    @classmethod
    def _missing_(cls, key: object) -> Literal[PressureUnit.unknown]:
        """Handle unknown pressure unit values."""

        msg: str = f"{key} pressure unit is unknown"
        LOG.warning(msg)
        return PressureUnit.unknown


class ScheduleType(StrEnum):
    """Enum representing the type of a schedule."""

    THERM = "therm"
    COOLING = "cooling"
    ELECTRICITY = "electricity"
    ELECTRICITY_PRODUCTION = "electricity_production"
    EVENT = "event"
    AUTO = "auto"
    ALGO = "algo"


class TemperatureControlMode(StrEnum):
    """Temperature control mode."""

    HEATING = "heating"
    COOLING = "cooling"


SCHEDULE_TYPE_MAPPING: dict[TemperatureControlMode, ScheduleType] = {
    TemperatureControlMode.HEATING: ScheduleType.THERM,
    TemperatureControlMode.COOLING: ScheduleType.COOLING,
}
