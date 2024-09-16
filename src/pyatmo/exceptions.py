"""Exceptions for pyatmo."""


class NoSchedule(Exception):
    """Raised when no schedule is found."""


class InvalidSchedule(Exception):
    """Raised when an invalid schedule is encountered."""


class InvalidHome(Exception):
    """Raised when an invalid home is encountered."""


class InvalidRoom(Exception):
    """Raised when an invalid room is encountered."""


class NoDevice(Exception):
    """Raised when no device is found."""


class ApiError(Exception):
    """Raised when an API error is encountered."""


class ApiErrorThrottling(ApiError):
    """Raised when an API error is encountered."""


class ApiHomeReachabilityError(ApiError):
    """Raised when an API error is encountered."""


class InvalidState(Exception):
    """Raised when an invalid state is encountered."""
