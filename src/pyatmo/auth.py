"""Support for Netatmo authentication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from json import JSONDecodeError
import logging
from typing import Any, Final

from aiohttp import (
    ClientError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ContentTypeError,
)
from tenacity import (
    RetryCallState,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_combine,
    wait_exponential,
    wait_random,
)

from pyatmo.const import (
    AUTHORIZATION_HEADER,
    CONCURRENCY_ERROR_CODE,
    DEFAULT_BASE_URL,
    ERRORS,
    FORBIDDEN_ERROR_CODE,
    THROTTLING_ERROR_CODE,
    TOO_MANY_REQUESTS_ERROR_CODE,
    WEBHOOK_URL_ADD_ENDPOINT,
    WEBHOOK_URL_DROP_ENDPOINT,
)
from pyatmo.exceptions import ApiError, ApiThrottlingError, ApiTooManyRequestError

LOG: logging.Logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT: Final[ClientTimeout] = ClientTimeout(total=20)

# Retries to official API on 429 concurrency errors
MAX_RETRIES = 4  # total attempts
INITIAL_BACKOFF = 1  # seconds
MULTIPLIER = 1
MAX_BACKOFF = 8  # cap on a single fallback wait
MAX_RETRY_AFTER = 60  # cap on an honored server Retry-After hint


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header (RFC 7231) into seconds.

    Accepts either a delta-seconds integer or an HTTP-date. Returns None when
    the header is absent or unparseable. A date in the past clamps to 0.
    """
    if not value:
        return None

    value = value.strip()
    if value.isdigit():
        return float(value)

    try:
        retry_date = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None

    if retry_date.tzinfo is None:
        retry_date = retry_date.replace(tzinfo=UTC)

    delta = (retry_date - datetime.now(UTC)).total_seconds()
    return max(delta, 0.0)


# Bounded exponential backoff with jitter. wait_exponential honors min/max
# on all supported tenacity versions (wait_random_exponential only respects
# min from 9.1.0), so combine it with wait_random for the jitter.
_fallback_wait = wait_combine(
    wait_exponential(multiplier=MULTIPLIER, min=INITIAL_BACKOFF, max=MAX_BACKOFF),
    wait_random(0, 1),
)


def _wait_retry_after(retry_state: RetryCallState) -> float:
    """Wait strategy honoring a server Retry-After, else bounded backoff.

    Prefers the ``retry_after`` carried by ``ApiTooManyRequestError`` (capped
    at ``MAX_RETRY_AFTER``); otherwise falls back to a jittered, bounded
    exponential backoff.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, ApiTooManyRequestError) and exc.retry_after is not None:
        return min(exc.retry_after, MAX_RETRY_AFTER)
    return _fallback_wait(retry_state)


class AbstractAsyncAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(
        self,
        websession: ClientSession,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Initialize the auth."""

        self.websession: ClientSession = websession
        self.base_url: str = base_url

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def async_get_image(
        self,
        endpoint: str,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> bytes:
        """Wrap async get requests."""

        # Note: the 429/concurrency retry lives on async_post_api_request only.
        # Camera snapshots are best-effort and time-sensitive - retrying a live
        # image seconds later has no value - so this path is deliberately not
        # decorated.
        try:
            access_token: str = await self.async_get_access_token()
        except ClientError as err:
            error_type: str = type(err).__name__
            msg: str = f"Access token failure: {error_type} - {err}"
            raise ApiError(msg) from err
        headers: dict[str, str] = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        url: str = (base_url or self.base_url) + endpoint
        async with self.websession.get(
            url,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as resp:
            resp_content: bytes = await resp.read()

            if resp.headers.get("content-type") == "image/jpeg":
                return resp_content

        msg = f"{resp.status} - invalid content-type in response when accessing '{url}'"
        raise ApiError(msg)

    @retry(
        retry=retry_if_exception_type(ApiTooManyRequestError),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=_wait_retry_after,
        before_sleep=before_sleep_log(LOG, logging.DEBUG),
        reraise=True,
    )
    async def async_post_api_request(
        self,
        endpoint: str,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> ClientResponse:
        """Wrap async post requests."""

        return await self.async_post_request(
            url=(base_url or self.base_url) + endpoint,
            params=params,
        )

    async def async_post_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> ClientResponse:
        """Wrap async post requests."""

        access_token: str = await self.get_access_token()
        headers: dict[str, str] = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        req_args: dict[str, Any] = self.prepare_request_arguments(params)

        async with self.websession.post(
            url,
            **req_args,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as resp:
            return await self.process_response(resp, url)

    async def get_access_token(self) -> str:
        """Get access token."""
        try:
            return await self.async_get_access_token()
        except ClientError as err:
            msg: str = f"Access token failure: {err}"
            raise ApiError(msg) from err

    def prepare_request_arguments(self, params: dict | None) -> dict:
        """Prepare request arguments."""
        req_args: dict[str, Any] = {"data": params if params is not None else {}}

        if "params" in req_args["data"]:
            req_args["params"] = req_args["data"]["params"]
            req_args["data"].pop("params")

        if "json" in req_args["data"]:
            req_args["json"] = req_args["data"]["json"]
            req_args.pop("data")

        return req_args

    async def process_response(self, resp: ClientResponse, url: str) -> ClientResponse:
        """Process response."""
        resp_status: int = resp.status
        resp_content: bytes = await resp.read()

        if not resp.ok:
            LOG.debug("The Netatmo API returned %s (%s)", resp_content, resp_status)
            await self.handle_error_response(resp, resp_status, url)

        return await self.handle_success_response(resp, resp_content)

    async def handle_error_response(
        self,
        resp: ClientResponse,
        resp_status: int,
        url: str,
    ) -> None:
        """Handle error response."""
        try:
            resp_json: dict[str, Any] = await resp.json()
            error: dict[str, Any] = resp_json.get("error", {})
            error_code = error.get("code")

            message: str = (
                f"{resp_status} - "
                f"{ERRORS.get(resp_status, '')} - "
                f"{error.get('message')} "
                f"({error_code}) "
                f"when accessing '{url}'"
            )

            if (
                resp_status == TOO_MANY_REQUESTS_ERROR_CODE
                and error_code == CONCURRENCY_ERROR_CODE
            ):
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                raise ApiTooManyRequestError(message, retry_after=retry_after)

            if (
                resp_status == FORBIDDEN_ERROR_CODE
                and error_code == THROTTLING_ERROR_CODE
            ):
                raise ApiThrottlingError(message)

            raise ApiError(message)

        except (JSONDecodeError, ContentTypeError) as exc:
            msg: str = (
                f"{resp_status} - "
                f"{ERRORS.get(resp_status, '')} - "
                f"when accessing '{url}'"
            )
            raise ApiError(msg) from exc

    async def handle_success_response(
        self,
        resp: ClientResponse,
        resp_content: bytes,
    ) -> ClientResponse:
        """Handle success response."""
        try:
            if "application/json" in resp.headers.get("content-type", []):
                return resp

            if resp_content not in [b"", b"None"]:
                return resp

        except (TypeError, AttributeError):
            LOG.debug("Invalid response %s", resp)

        return resp

    async def async_addwebhook(self, webhook_url: str) -> None:
        """Register webhook."""
        try:
            resp: ClientResponse = await self.async_post_api_request(
                endpoint=WEBHOOK_URL_ADD_ENDPOINT,
                params={"url": webhook_url},
            )
        except TimeoutError as exc:
            msg: str = "Webhook registration timed out"
            raise ApiError(msg) from exc
        else:
            LOG.debug("addwebhook: %s", resp)

    async def async_dropwebhook(self) -> None:
        """Unregister webhook."""
        try:
            resp: ClientResponse = await self.async_post_api_request(
                endpoint=WEBHOOK_URL_DROP_ENDPOINT,
                params={"app_types": "app_security"},
            )
        except TimeoutError as exc:
            msg: str = "Webhook registration timed out"
            raise ApiError(msg) from exc
        else:
            LOG.debug("dropwebhook: %s", resp)
