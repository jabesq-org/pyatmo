"""Exceptions for pyatmo."""


class NoScheduleError(Exception):
    """Raised when no schedule is found."""


class InvalidScheduleError(Exception):
    """Raised when an invalid schedule is encountered."""


class InvalidRoomError(Exception):
    """Raised when an invalid room is encountered."""


class NoDeviceError(Exception):
    """Raised when no device is found."""


class ApiError(Exception):
    """Raised when an API error is encountered."""


class InvalidHomeError(ApiError):
    """Raised when the API rejects a home id.

    Deterministic: the same home id will be rejected on every future call, so a
    caller should stop polling that home rather than retry it.
    """


class ApiThrottlingError(ApiError):
    """Raised when an API error is encountered."""


class ApiHomeReachabilityError(ApiError):
    """Raised when an API error is encountered."""


class InvalidStateError(Exception):
    """Raised when an invalid state is encountered."""


class ApiTooManyRequestError(ApiError):
    """Raised when API returned 429 code 11."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Initialize with an optional server-provided retry delay (seconds)."""
        super().__init__(message)
        self.retry_after = retry_after
