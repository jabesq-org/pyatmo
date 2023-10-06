"""Exceptions for pyatmo."""


class NoSchedule(Exception):
    """Raised when no schedule is found."""

    pass


class InvalidSchedule(Exception):
    """Raised when an invalid schedule is encountered."""

    pass


class InvalidHome(Exception):
    """Raised when an invalid home is encountered."""

    pass


class InvalidRoom(Exception):
    """Raised when an invalid room is encountered."""

    pass


class NoDevice(Exception):
    """Raised when no device is found."""

    pass


class ApiError(Exception):
    """Raised when an API error is encountered."""

    pass


class InvalidState(Exception):
    """Raised when an invalid state is encountered."""

    pass
