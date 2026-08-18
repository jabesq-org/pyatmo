"""Support for Netatmo authentication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from json import JSONDecodeError
import logging
from typing import Any, Final
from urllib.parse import urlsplit, urlunsplit

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
    CONFLICT_ERROR_CODE,
    DEFAULT_BASE_URL,
    ERRORS,
    FORBIDDEN_ERROR_CODE,
    HOME,
    THROTTLING_ERROR_CODE,
    TOO_MANY_REQUESTS_ERROR_CODE,
    WEBHOOK_ENDPOINT,
)
from pyatmo.exceptions import ApiError, ApiThrottlingError, ApiTooManyRequestError
from pyatmo.helpers import home_suffix

LOG: logging.Logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT: Final[ClientTimeout] = ClientTimeout(total=20)

# Retries to official API on 429 concurrency errors
MAX_RETRIES = 4  # total attempts
INITIAL_BACKOFF = 1  # seconds
MULTIPLIER = 1
MAX_BACKOFF = 8  # cap on a single fallback wait
MAX_RETRY_AFTER = 60  # cap on an honored server Retry-After hint

# Rendering of a webhook URL for logs - see _redact_webhook_url.
REDACTED_PLACEHOLDER: Final[str] = "<redacted>"
REDACTED_TAIL_LENGTH: Final[int] = 4


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


def _redact_webhook_url(url: str) -> str:
    """Render a webhook URL in a form that is safe to log.

    A webhook URL is a capability URL: the URL is itself the credential, and
    anyone holding it can POST forged Netatmo events into the consumer's
    instance.
    DEBUG is exactly the level users are asked to enable when filing a bug
    report, so a URL logged whole ends up attached to public issues.

    Keeps the scheme and host - enough to tell a Nabu Casa cloudhook from a
    self-hosted endpoint - elides the path, and keeps a short tail so a reader
    can tell two webhooks apart and follow one across log lines. Those few
    characters of a high-entropy path cannot be reconstructed from, but they do
    reach the log: the trade is deliberate, not an oversight. Anything without
    a recognizable scheme and host is redacted whole, since its shape gives no
    reason to believe any part is safe.

    Never raises: a logging helper that throws would break the very caller it
    is meant to protect.
    """
    try:
        parts = urlsplit(url)
        # hostname, never netloc: netloc carries userinfo, and a webhook URL
        # behind a basic-auth proxy would otherwise publish its password.
        host: str | None = parts.hostname
        if not parts.scheme or not host:
            return REDACTED_PLACEHOLDER

        origin: str = f"{parts.scheme}://{host}"
        if parts.port is not None:
            origin = f"{origin}:{parts.port}"

        # Everything after the authority is the capability secret. Rebuilt from
        # the parsed parts rather than sliced off the input, because the
        # rendered origin is no longer the same length as what it replaced.
        path: str = urlunsplit(("", "", parts.path, parts.query, parts.fragment))
    except (AttributeError, TypeError, ValueError):
        return REDACTED_PLACEHOLDER

    if not path:
        return origin

    # Only keep a tail when the path is long enough that the tail is a small
    # part of it - four of five characters would be worse than none.
    if len(path) > 2 * REDACTED_TAIL_LENGTH:
        return f"{origin}/...{path[-REDACTED_TAIL_LENGTH:]}"

    return f"{origin}/..."


def _home_suffix(params: dict[str, Any] | None) -> str:
    """Postfix a log message with the home the request names."""
    params = params or {}

    home_id: Any = params.get("home_id")
    if not home_id:
        body: Any = params.get("json")
        home: Any = body.get(HOME) if isinstance(body, dict) else None
        home_id = home.get("id") if isinstance(home, dict) else None

    return home_suffix(home_id if isinstance(home_id, str) else None)


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

        # Note: the 429/concurrency retry lives on the *_api_request wrappers.
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
            return await self.process_response(resp, url, params=params)

    @retry(
        retry=retry_if_exception_type(ApiTooManyRequestError),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=_wait_retry_after,
        before_sleep=before_sleep_log(LOG, logging.DEBUG),
        reraise=True,
    )
    async def async_get_api_request(
        self,
        endpoint: str,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> ClientResponse:
        """Wrap async get requests returning JSON."""

        return await self.async_get_request(
            url=(base_url or self.base_url) + endpoint,
            params=params,
        )

    async def async_get_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> ClientResponse:
        """Wrap async get requests returning JSON."""

        access_token: str = await self.get_access_token()
        headers: dict[str, str] = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        async with self.websession.get(
            url,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as resp:
            return await self.process_response(resp, url, params=params)

    @retry(
        retry=retry_if_exception_type(ApiTooManyRequestError),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=_wait_retry_after,
        before_sleep=before_sleep_log(LOG, logging.DEBUG),
        reraise=True,
    )
    async def async_delete_api_request(
        self,
        endpoint: str,
        base_url: str | None = None,
    ) -> ClientResponse:
        """Wrap async delete requests."""

        return await self.async_delete_request(
            url=(base_url or self.base_url) + endpoint,
        )

    async def async_delete_request(self, url: str) -> ClientResponse:
        """Wrap async delete requests."""

        access_token: str = await self.get_access_token()
        headers: dict[str, str] = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        async with self.websession.delete(
            url,
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

    async def process_response(
        self,
        resp: ClientResponse,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> ClientResponse:
        """Process response.

        ``params`` is the request payload; it is used solely to name the home
        the failed request was for - the home id travels in the body, not the
        URL, so an error is otherwise unattributable.
        """
        resp_status: int = resp.status
        resp_content: bytes = await resp.read()

        if not resp.ok:
            LOG.debug(
                "The Netatmo API returned %s (%s)%s",
                resp_content,
                resp_status,
                _home_suffix(params),
            )
            await self.handle_error_response(resp, resp_status, url, params)

        return await self.handle_success_response(resp, resp_content)

    async def handle_error_response(
        self,
        resp: ClientResponse,
        resp_status: int,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Handle error response."""
        suffix: str = _home_suffix(params)

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
                f"{suffix}"
            )

            if (
                resp_status == TOO_MANY_REQUESTS_ERROR_CODE
                and error_code == CONCURRENCY_ERROR_CODE
            ):
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                raise ApiTooManyRequestError(
                    message,
                    retry_after=retry_after,
                    status=resp_status,
                    code=error_code,
                )

            if (
                resp_status == FORBIDDEN_ERROR_CODE
                and error_code == THROTTLING_ERROR_CODE
            ):
                raise ApiThrottlingError(message, status=resp_status, code=error_code)

            # Deliberately no special case for a rejected home id here: the
            # code that says so - 21 - is a generic invalid-parameter code that
            # addwebhook also answers a bad URL with, and this layer sees only a
            # status, a code and a URL. Callers with the request context in hand
            # read the code off the exception; see AsyncAccount.async_update_status.
            raise ApiError(message, status=resp_status, code=error_code)

        except (JSONDecodeError, ContentTypeError) as exc:
            msg: str = (
                f"{resp_status} - "
                f"{ERRORS.get(resp_status, '')} - "
                f"when accessing '{url}'"
                f"{suffix}"
            )
            # No code: the body that would have carried it could not be read.
            raise ApiError(msg, status=resp_status) from exc

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
        """Register a webhook URL for this application."""
        try:
            resp: ClientResponse = await self._async_post_webhook(webhook_url)
        except ApiError as exc:
            if exc.status != CONFLICT_ERROR_CODE:
                raise

            # One webhook per application: clear the incumbent and try once
            # more. A second conflict is surfaced rather than retried.
            try:
                await self.async_delete_api_request(endpoint=WEBHOOK_ENDPOINT)
            except TimeoutError as timeout:
                msg = "Webhook removal during replacement timed out"
                raise ApiError(msg) from timeout

            resp = await self._async_post_webhook(webhook_url)

        LOG.debug("addwebhook: %s", resp)

    async def _async_post_webhook(self, webhook_url: str) -> ClientResponse:
        """POST the registration, reporting a timeout as an ApiError."""
        try:
            return await self.async_post_api_request(
                endpoint=WEBHOOK_ENDPOINT,
                params={"json": {"url": webhook_url}},
            )
        except TimeoutError as exc:
            msg: str = "Webhook registration timed out"
            raise ApiError(msg) from exc

    async def async_dropwebhook(self) -> None:
        """Unregister this application's webhook."""
        try:
            resp: ClientResponse = await self.async_delete_api_request(
                endpoint=WEBHOOK_ENDPOINT,
            )
        except TimeoutError as exc:
            msg: str = "Webhook removal timed out"
            raise ApiError(msg) from exc
        else:
            LOG.debug("dropwebhook: %s", resp)

    async def async_list_webhooks(self) -> list[str]:
        """Return the webhook URLs currently registered for this application."""
        try:
            resp: ClientResponse = await self.async_get_api_request(
                endpoint=WEBHOOK_ENDPOINT,
            )
        except TimeoutError as exc:
            msg: str = "Webhook listing timed out"
            raise ApiError(msg) from exc

        try:
            resp_json: Any = await resp.json()
        except (JSONDecodeError, ContentTypeError) as exc:
            msg = "Invalid response when listing webhooks"
            raise ApiError(msg) from exc

        body: Any = resp_json.get("body") if isinstance(resp_json, dict) else None
        if not isinstance(body, list):
            # Messages carry types only - a webhook URL is a capability URL.
            msg = f"Unexpected payload when listing webhooks: {type(body).__name__}"
            raise ApiError(msg)

        webhooks: list[str] = []
        for entry in body:
            url: Any = entry.get("url") if isinstance(entry, dict) else None
            if not isinstance(url, str):
                # Keys only, never values, for the same reason.
                detail: Any = (
                    sorted(entry) if isinstance(entry, dict) else type(entry).__name__
                )
                msg = f"Unexpected webhook entry when listing webhooks: {detail}"
                raise ApiError(msg)
            webhooks.append(url)

        # Count first: it is the part a health check reads. The URLs are
        # capability URLs, so they are only ever rendered redacted.
        LOG.debug(
            "list_webhooks: %s registered %s",
            len(webhooks),
            [_redact_webhook_url(url) for url in webhooks],
        )

        return webhooks
