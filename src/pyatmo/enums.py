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
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object) -> Literal[UnitSystem.UNKNOWN]:
        """Handle unknown unit system values."""

        msg: str = f"{value} unit system is unknown"
        LOG.warning(msg)
        return UnitSystem.UNKNOWN


class WindUnit(IntEnum):
    """Wind-speed unit reported in the /homesdata user block."""

    KPH = 0
    MPH = 1
    MS = 2
    BEAUFORT = 3
    KNOT = 4
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object) -> Literal[WindUnit.UNKNOWN]:
        """Handle unknown wind unit values."""

        msg: str = f"{value} wind unit is unknown"
        LOG.warning(msg)
        return WindUnit.UNKNOWN


class PressureUnit(IntEnum):
    """Pressure unit reported in the /homesdata user block."""

    MBAR = 0
    INHG = 1
    MMHG = 2
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value: object) -> Literal[PressureUnit.UNKNOWN]:
        """Handle unknown pressure unit values."""

        msg: str = f"{value} pressure unit is unknown"
        LOG.warning(msg)
        return PressureUnit.UNKNOWN


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
    AUTO = "auto"


SCHEDULE_TYPE_MAPPING: dict[TemperatureControlMode, ScheduleType] = {
    TemperatureControlMode.HEATING: ScheduleType.THERM,
    TemperatureControlMode.COOLING: ScheduleType.COOLING,
    TemperatureControlMode.AUTO: ScheduleType.AUTO,
}
