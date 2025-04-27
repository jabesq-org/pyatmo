"""Enums for the pyatmo package."""

from enum import StrEnum


class ScheduleType(StrEnum):
    """Enum representing the type of a schedule."""

    THERM = "therm"
    COOLING = "cooling"
    ELECTRICITY = "electricity"
    EVENT = "event"
    AUTO = "auto"


class TemperatureControlMode(StrEnum):
    """Temperature control mode."""

    HEATING = "heating"
    COOLING = "cooling"


SCHEDULE_TYPE_MAPPING = {
    TemperatureControlMode.HEATING: ScheduleType.THERM,
    TemperatureControlMode.COOLING: ScheduleType.COOLING,
}
