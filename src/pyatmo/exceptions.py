"""Exceptions for pyatmo."""


class NoScheduleError(Exception):
    """Raised when no schedule is found."""


class InvalidScheduleError(Exception):
    """Raised when an invalid schedule is encountered."""


class InvalidHomeError(Exception):
    """Raised when an invalid home is encountered."""


class InvalidRoomError(Exception):
    """Raised when an invalid room is encountered."""


class NoDeviceError(Exception):
    """Raised when no device is found."""


class ApiError(Exception):
    """Raised when an API error is encountered."""


class ApiThrottlingError(ApiError):
    """Raised when an API error is encountered."""


class ApiHomeReachabilityError(ApiError):
    """Raised when an API error is encountered."""


class InvalidStateError(Exception):
    """Raised when an invalid state is encountered."""
