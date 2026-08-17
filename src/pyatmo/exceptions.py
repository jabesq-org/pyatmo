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
    """Raised when an API error is encountered.

    ``status`` (the HTTP status) and ``code`` (the Netatmo error code) are
    carried whenever the response yielded them, and are ``None`` otherwise -
    an unreadable body still produces an error, just without a code.

    They exist because Netatmo reuses one code across unrelated endpoints:
    ``400`` + code 21 answers both a rejected home id and an ``addwebhook``
    URL whose host does not resolve. Only a caller that knows what it asked
    for can turn such a pair into a specific exception.

    ``code`` is typed ``int | str`` because Netatmo is not consistent: the
    legacy ``api/*`` endpoints answer with integers (11, 21, 26), while
    ``webhooks/v1`` answers with strings such as ``"WH009"``. Whatever arrived
    is passed through unconverted, so a comparison against an integer code
    simply does not match a string one.
    """

    def __init__(
        self,
        message: str = "",
        status: int | None = None,
        code: int | str | None = None,
    ) -> None:
        """Initialize with the HTTP status and Netatmo error code, when known.

        ``message`` defaults so that ``ApiError()`` keeps working: this class
        inherited ``Exception.__init__`` before it carried a status and a code,
        and it is public API.
        """
        super().__init__(message)
        self.status = status
        self.code = code


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

    def __init__(
        self,
        message: str = "",
        retry_after: float | None = None,
        status: int | None = None,
        code: int | str | None = None,
    ) -> None:
        """Initialize with an optional server-provided retry delay (seconds)."""
        super().__init__(message, status=status, code=code)
        self.retry_after = retry_after
