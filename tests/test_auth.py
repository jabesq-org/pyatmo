"""Tests for pyatmo.auth retry / 429 concurrency handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from json import JSONDecodeError
import logging

from aiohttp import ContentTypeError
import pytest
from tenacity import Future, RetryCallState

from pyatmo.auth import (
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RETRIES,
    MAX_RETRY_AFTER,
    AbstractAsyncAuth,
    _parse_retry_after,
    _redact_webhook_url,
    _wait_retry_after,
)
from pyatmo.exceptions import (
    ApiError,
    ApiThrottlingError,
    ApiTooManyRequestError,
    InvalidHomeError,
)

from .common import MockResponse


class _Auth(AbstractAsyncAuth):
    """Concrete auth for exercising error handling."""

    async def async_get_access_token(self) -> str:
        return "token"


@pytest.fixture
def auth():
    return _Auth(websession=None)


def _retry_state(exc: BaseException | None, attempt_number: int = 1) -> RetryCallState:
    """Build a minimal RetryCallState whose outcome raised ``exc``."""
    state = RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
    state.attempt_number = attempt_number
    future = Future(attempt_number)
    if exc is not None:
        future.set_exception(exc)
    else:
        future.set_result(None)
    state.outcome = future
    return state


def test_too_many_request_error_carries_retry_after():
    """ApiTooManyRequestError exposes retry_after and is an ApiError."""
    err = ApiTooManyRequestError("boom", retry_after=12.0)

    assert isinstance(err, ApiError)
    assert err.retry_after == 12.0


def test_too_many_request_error_defaults_retry_after_none():
    """retry_after defaults to None when not provided."""
    assert ApiTooManyRequestError("boom").retry_after is None


def test_parse_retry_after_delta_seconds():
    """A numeric Retry-After header parses to float seconds."""
    assert _parse_retry_after("5") == 5.0
    assert _parse_retry_after(" 5 ") == 5.0
    assert _parse_retry_after("005") == 5.0


def test_parse_retry_after_empty_or_none():
    """Missing header yields None."""
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("") is None


def test_parse_retry_after_http_date_future():
    """An HTTP-date in the future yields a positive delay."""
    future = datetime.now(UTC) + timedelta(seconds=30)
    value = format_datetime(future, usegmt=True)

    result = _parse_retry_after(value)

    assert result is not None
    assert 20 <= result <= 30


def test_parse_retry_after_http_date_past_clamped_to_zero():
    """An HTTP-date in the past clamps to 0."""
    past = datetime.now(UTC) - timedelta(seconds=30)
    value = format_datetime(past, usegmt=True)

    assert _parse_retry_after(value) == 0.0


def test_parse_retry_after_garbage():
    """Unparseable header yields None."""
    assert _parse_retry_after("not-a-date") is None


def test_wait_retry_after_uses_server_hint():
    """When the exception carries retry_after, that value drives the wait."""
    state = _retry_state(ApiTooManyRequestError("boom", retry_after=3.0))

    assert _wait_retry_after(state) == 3.0


def test_wait_retry_after_caps_server_hint():
    """A huge server hint is capped to MAX_RETRY_AFTER."""
    state = _retry_state(ApiTooManyRequestError("boom", retry_after=9999.0))

    assert _wait_retry_after(state) == MAX_RETRY_AFTER


def test_wait_retry_after_falls_back_without_hint():
    """No server hint -> bounded exponential fallback."""
    state = _retry_state(
        ApiTooManyRequestError("boom", retry_after=None),
        attempt_number=1,
    )

    result = _wait_retry_after(state)

    assert INITIAL_BACKOFF <= result <= MAX_BACKOFF + 1


def test_wait_retry_after_falls_back_for_other_exception():
    """A non-ApiTooManyRequestError outcome uses the fallback wait."""
    state = _retry_state(ApiError("other"))

    result = _wait_retry_after(state)

    assert INITIAL_BACKOFF <= result <= MAX_BACKOFF + 1


async def test_handle_error_429_code_11_raises_too_many_with_retry_after(auth):
    """429 + concurrency code 11 raises ApiTooManyRequestError w/ parsed hint."""
    resp = MockResponse(
        {"error": {"code": 11, "message": "concurrency"}},
        429,
        headers={"Retry-After": "7"},
    )

    with pytest.raises(ApiTooManyRequestError) as exc_info:
        await auth.handle_error_response(resp, 429, "https://x/y")

    assert exc_info.value.retry_after == 7.0


async def test_handle_error_429_code_11_without_header(auth):
    """No Retry-After header -> retry_after is None."""
    resp = MockResponse({"error": {"code": 11, "message": "concurrency"}}, 429)

    with pytest.raises(ApiTooManyRequestError) as exc_info:
        await auth.handle_error_response(resp, 429, "https://x/y")

    assert exc_info.value.retry_after is None


async def test_handle_error_403_code_26_raises_throttling(auth):
    """403 + code 26 raises ApiThrottlingError, not the 429 type."""
    resp = MockResponse({"error": {"code": 26, "message": "throttled"}}, 403)

    with pytest.raises(ApiThrottlingError):
        await auth.handle_error_response(resp, 403, "https://x/y")


async def test_handle_error_missing_error_key_no_keyerror(auth):
    """A body without an 'error' object raises ApiError, not KeyError."""
    resp = MockResponse({"status": "error"}, 500)

    with pytest.raises(ApiError):
        await auth.handle_error_response(resp, 500, "https://x/y")


async def test_post_api_request_retries_then_succeeds(auth):
    """A transient 429/code-11 is retried and the eventual success returned."""
    success = MockResponse({"status": "ok"}, 200)
    calls = 0

    busy = "busy"

    async def flaky(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ApiTooManyRequestError(busy, retry_after=0.0)
        return success

    auth.async_post_request = flaky

    result = await auth.async_post_api_request(endpoint="api/homestatus")

    assert result is success
    assert calls == 3


async def test_post_api_request_reraises_after_exhaustion(auth):
    """Persistent 429/code-11 reraises ApiTooManyRequestError after MAX_RETRIES."""
    calls = 0
    busy = "busy"

    async def always_busy(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise ApiTooManyRequestError(busy, retry_after=0.0)

    auth.async_post_request = always_busy

    with pytest.raises(ApiTooManyRequestError):
        await auth.async_post_api_request(endpoint="api/homestatus")

    assert calls == MAX_RETRIES


async def test_post_api_request_does_not_retry_other_errors(auth):
    """A generic ApiError is not retried."""
    calls = 0
    nope = "nope"

    async def boom(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise ApiError(nope)

    auth.async_post_request = boom

    with pytest.raises(ApiError):
        await auth.async_post_api_request(endpoint="api/homestatus")

    assert calls == 1


# Obviously fake, shaped like a Nabu Casa cloudhook. Never use a real one: a
# webhook URL is a capability URL, and this file is public.
FAKE_SECRET = "gAAAAABn0tR34LacApab1l1tyUrlJUSTF4KEd0N0tUs3z9Qb="
FAKE_CLOUDHOOK = f"https://hooks.nabu.casa/{FAKE_SECRET}"


def test_redact_webhook_url_keeps_origin_elides_secret_keeps_tail():
    """The scheme and host survive; the capability secret does not.

    The host distinguishes a Nabu Casa cloudhook from a self-hosted endpoint,
    and the short tail lets a reader correlate the same webhook across log
    lines without holding anything usable.
    """
    redacted = _redact_webhook_url(FAKE_CLOUDHOOK)

    assert redacted == "https://hooks.nabu.casa/...9Qb="
    assert FAKE_SECRET not in redacted
    assert FAKE_SECRET[:-4] not in redacted


def test_redact_webhook_url_keeps_a_self_hosted_host():
    """A self-hosted endpoint stays recognizable as such."""
    redacted = _redact_webhook_url(
        "https://hass.example.org:8123/api/webhook/s3cr3t-webhook-id-4242",
    )

    assert redacted == "https://hass.example.org:8123/...4242"
    assert "s3cr3t-webhook-id" not in redacted
    assert "/api/webhook/" not in redacted


def test_redact_webhook_url_without_path_returns_the_origin():
    """No path means no secret to elide."""
    assert _redact_webhook_url("https://example.com") == "https://example.com"


def test_redact_webhook_url_short_path_keeps_no_tail():
    """A path too short to keep a tail from is elided whole.

    Showing four of five secret characters would be worse than showing none.
    """
    redacted = _redact_webhook_url("https://example.com/s3cr3t")

    assert redacted == "https://example.com/..."
    assert "s3cr3t" not in redacted


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-url",
        "hooks.nabu.casa/s3cr3t",
        "/api/webhook/s3cr3t",
        "https:///s3cr3t",
        "s3cr3t",
    ],
)
def test_redact_webhook_url_redacts_anything_without_an_origin(value):
    """Without a recognizable scheme and host, nothing is assumed safe."""
    redacted = _redact_webhook_url(value)

    assert redacted == "<redacted>"
    assert "s3cr3t" not in redacted


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "https://[oops",
        "https://[::1",
        "http://",
        "://",
        "\x00",
        "https://example.com/" + "x" * 10000,
        FAKE_CLOUDHOOK,
    ],
)
def test_redact_webhook_url_never_raises(value):
    """A logging helper that throws would break the caller it was meant to protect."""
    assert isinstance(_redact_webhook_url(value), str)


def _stub_get(auth, payload=None, exc=None):
    """Replace the auth GET transport with a stub returning ``payload``."""
    seen = {}

    async def fake_get(*_args, **kwargs):
        seen.update(kwargs)
        if exc is not None:
            raise exc
        return MockResponse(payload, 200)

    auth.async_get_request = fake_get
    return seen


async def test_list_webhooks_returns_registered_url(auth):
    """A registered webhook is returned as a single-entry list."""
    _stub_get(auth, {"status": "ok", "body": [{"url": "https://example.com/hook"}]})

    assert await auth.async_list_webhooks() == ["https://example.com/hook"]


async def test_list_webhooks_hits_expected_url(auth):
    """The listing endpoint is appended to the base URL without an api/ prefix."""
    seen = _stub_get(auth, {"status": "ok", "body": []})

    await auth.async_list_webhooks()

    assert seen["url"] == "https://api.netatmo.com/webhooks/v1/"


async def test_list_webhooks_empty_body(auth):
    """No registered webhook yields an empty list."""
    _stub_get(auth, {"status": "ok", "body": []})

    assert await auth.async_list_webhooks() == []


async def test_list_webhooks_multiple_urls_in_order(auth):
    """Several registered webhooks are all returned, in payload order."""
    _stub_get(
        auth,
        {
            "status": "ok",
            "body": [
                {"url": "https://a.example.com/hook"},
                {"url": "https://b.example.com/hook"},
            ],
        },
    )

    assert await auth.async_list_webhooks() == [
        "https://a.example.com/hook",
        "https://b.example.com/hook",
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "ok"},
        {"status": "ok", "body": None},
        {"status": "ok", "body": {"url": "https://example.com/hook"}},
        {"status": "ok", "body": "nope"},
        [],
        None,
    ],
)
async def test_list_webhooks_unexpected_shape_raises_api_error(auth, payload):
    """A missing or non-list body is a failed check, not a confirmed absence.

    Returning [] here would tell a caller no webhook is registered, which an
    unreadable answer does not prove.
    """
    _stub_get(auth, payload)

    with pytest.raises(ApiError, match="Unexpected payload when listing webhooks"):
        await auth.async_list_webhooks()


@pytest.mark.parametrize(
    "entry",
    [
        {"app_type": "app_security"},
        "not-a-dict",
        {"url": None},
    ],
)
async def test_list_webhooks_unexpected_entry_raises_api_error(auth, entry):
    """An entry without a usable 'url' means the listing cannot be trusted.

    Skipping it could hide our own registration and read as an absence.
    """
    _stub_get(
        auth,
        {"status": "ok", "body": [entry, {"url": "https://example.com/hook"}]},
    )

    with pytest.raises(ApiError, match="Unexpected webhook entry"):
        await auth.async_list_webhooks()


async def test_list_webhooks_error_message_omits_urls(auth):
    """A malformed entry is reported by its keys, never its values.

    A webhook URL is a capability URL; it must not reach an exception message.
    """
    _stub_get(
        auth,
        {
            "status": "ok",
            "body": [{"uri": "https://secret.example.com/hook"}],
        },
    )

    with pytest.raises(ApiError) as excinfo:
        await auth.async_list_webhooks()

    assert "secret.example.com" not in str(excinfo.value)
    assert "uri" in str(excinfo.value)


async def test_list_webhooks_propagates_api_error(auth):
    """An API error from the request path propagates untouched."""
    boom = "boom"
    _stub_get(auth, exc=ApiError(boom))

    with pytest.raises(ApiError, match=boom):
        await auth.async_list_webhooks()


async def test_list_webhooks_timeout_raises_api_error(auth):
    """A TimeoutError surfaces as ApiError, like the add/drop helpers."""
    _stub_get(auth, exc=TimeoutError)

    with pytest.raises(ApiError, match="timed out"):
        await auth.async_list_webhooks()


class _UnparsableResponse(MockResponse):
    """A 200 response whose body cannot be parsed as JSON."""

    def __init__(self, exc):
        super().__init__(None, 200)
        self._exc = exc

    async def json(self):
        raise self._exc


@pytest.mark.parametrize(
    "exc",
    [
        ContentTypeError(None, ()),
        JSONDecodeError("Expecting value", "<html>", 0),
    ],
)
async def test_list_webhooks_unparsable_body_raises_api_error(auth, exc):
    """A 200 that is not JSON raises ApiError instead of leaking aiohttp errors.

    handle_success_response deliberately passes a non-JSON body through, so the
    parse failure surfaces here - e.g. a proxy returning an HTML error page.
    """

    async def fake_get(*_args, **_kwargs):
        return _UnparsableResponse(exc)

    auth.async_get_request = fake_get

    with pytest.raises(ApiError, match="Invalid response when listing webhooks"):
        await auth.async_list_webhooks()


async def test_list_webhooks_debug_log_redacts_the_url(auth, caplog):
    """DEBUG is what users enable to file a bug report, so it reaches issues.

    The registered URL must therefore never reach the log in full: anyone
    holding it can POST forged Netatmo events into that user's instance.
    """
    _stub_get(auth, {"status": "ok", "body": [{"url": FAKE_CLOUDHOOK}]})

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"):
        await auth.async_list_webhooks()

    assert FAKE_SECRET not in caplog.text
    assert FAKE_SECRET[:-4] not in caplog.text
    assert "list_webhooks: 1 registered" in caplog.text
    assert "https://hooks.nabu.casa/...9Qb=" in caplog.text


async def test_list_webhooks_debug_log_counts_every_url(auth, caplog):
    """The count is the useful part, and it stays truthful for several hooks."""
    _stub_get(
        auth,
        {
            "status": "ok",
            "body": [
                {"url": "https://a.example.com/s3cr3t-aaaa"},
                {"url": "https://b.example.com/s3cr3t-bbbb"},
            ],
        },
    )

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"):
        await auth.async_list_webhooks()

    assert "list_webhooks: 2 registered" in caplog.text
    assert "s3cr3t" not in caplog.text
    assert "https://a.example.com/...aaaa" in caplog.text
    assert "https://b.example.com/...bbbb" in caplog.text


async def test_list_webhooks_debug_log_reports_zero(auth, caplog):
    """An empty listing is the interesting case for a health check."""
    _stub_get(auth, {"status": "ok", "body": []})

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"):
        await auth.async_list_webhooks()

    assert "list_webhooks: 0 registered" in caplog.text


class _ReprResponse(MockResponse):
    """A response whose repr matches aiohttp's ClientResponse.__repr__.

    aiohttp renders ``<ClientResponse(<request url>) [<status> <reason>]>``
    followed by the response headers, so a repr can only leak what the request
    URL carried.
    """

    def __init__(self, url, status=200, headers=None):
        super().__init__({"status": "ok"}, status, headers)
        self.url = url

    def __repr__(self):
        return f"<ClientResponse({self.url}) [{self.status} OK]>\n{self.headers}\n"


class _RecordingSession:
    """Session capturing how the request was built, returning a repr-faithful response."""

    def __init__(self):
        self.seen = {}

    def post(self, url, **kwargs):
        self.seen["url"] = url
        self.seen.update(kwargs)
        return _ReprResponse(url)


async def test_addwebhook_sends_the_url_in_the_body_not_the_query():
    """The registration URL must stay out of the request URL.

    ``async_addwebhook`` logs the ClientResponse, whose repr renders the
    request URL. That is only safe while the webhook URL travels as form data.
    """
    session = _RecordingSession()
    auth = _Auth(websession=session)

    await auth.async_addwebhook(FAKE_CLOUDHOOK)

    assert session.seen["url"] == "https://api.netatmo.com/api/addwebhook"
    assert session.seen["data"] == {"url": FAKE_CLOUDHOOK}
    assert "params" not in session.seen


async def test_addwebhook_debug_log_does_not_leak_the_url(caplog):
    """The addwebhook debug line renders a response, never the registered URL."""
    auth = _Auth(websession=_RecordingSession())

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"):
        await auth.async_addwebhook(FAKE_CLOUDHOOK)

    assert FAKE_SECRET not in caplog.text
    assert "hooks.nabu.casa" not in caplog.text
    assert "addwebhook:" in caplog.text


async def test_get_request_uses_bearer_token_and_returns_response():
    """The GET transport sends the bearer header and returns the response."""
    resp = MockResponse(
        {"status": "ok", "body": [{"url": "https://example.com/hook"}]},
        200,
        headers={"content-type": "application/json"},
    )
    seen = {}

    class _Session:
        def get(self, url, **kwargs):
            seen["url"] = url
            seen.update(kwargs)
            return resp

    auth = _Auth(websession=_Session())

    assert await auth.async_list_webhooks() == ["https://example.com/hook"]
    assert seen["url"] == "https://api.netatmo.com/webhooks/v1/"
    assert seen["headers"] == {"Authorization": "Bearer token"}


async def test_get_request_error_response_raises_api_error():
    """A non-ok response on the GET path goes through the shared error handling."""

    class _Session:
        def get(self, _url, **_kwargs):
            return MockResponse({"error": {"code": 2, "message": "nope"}}, 400)

    auth = _Auth(websession=_Session())

    with pytest.raises(ApiError):
        await auth.async_list_webhooks()


async def test_get_api_request_retries_then_succeeds(auth):
    """A transient 429/code-11 on the GET path is retried, then succeeds."""
    success = MockResponse({"status": "ok"}, 200)
    calls = 0
    busy = "busy"

    async def flaky(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ApiTooManyRequestError(busy, retry_after=0.0)
        return success

    auth.async_get_request = flaky

    result = await auth.async_get_api_request(endpoint="webhooks/v1/")

    assert result is success
    assert calls == 3


async def test_get_api_request_reraises_after_exhaustion(auth):
    """Persistent 429/code-11 reraises ApiTooManyRequestError after MAX_RETRIES."""
    calls = 0
    busy = "busy"

    async def always_busy(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise ApiTooManyRequestError(busy, retry_after=0.0)

    auth.async_get_request = always_busy

    with pytest.raises(ApiTooManyRequestError):
        await auth.async_get_api_request(endpoint="webhooks/v1/")

    assert calls == MAX_RETRIES


async def test_handle_error_400_code_21_raises_invalid_home(auth):
    """400 + code 21 raises InvalidHomeError, not a bare ApiError."""
    resp = MockResponse({"error": {"code": 21, "message": "Invalid home_id"}}, 400)

    with pytest.raises(InvalidHomeError):
        await auth.handle_error_response(resp, 400, "https://x/y")


async def test_handle_error_400_without_code_21_stays_generic(auth):
    """Another 400 is still an ApiError, so only the known code is special-cased."""
    resp = MockResponse({"error": {"code": 2, "message": "Invalid access token"}}, 400)

    with pytest.raises(ApiError):
        await auth.handle_error_response(resp, 400, "https://x/y")


def test_invalid_home_error_is_an_api_error():
    """Consumers catching ApiError keep catching this one."""
    assert issubclass(InvalidHomeError, ApiError)


async def test_handle_error_names_the_home_from_params(auth):
    """The rejected home id reaches the exception message.

    The home id travels in the POST body, not the URL, so without this a
    consumer cannot tell which of its homes the API rejected.
    """
    resp = MockResponse({"error": {"code": 21, "message": "Invalid home_id"}}, 400)

    with pytest.raises(InvalidHomeError) as exc_info:
        await auth.handle_error_response(
            resp,
            400,
            "https://x/homestatus",
            params={"home_id": "5ed02c730474377f3443794a"},
        )

    assert "for home 5ed02c730474377f3443794a" in str(exc_info.value)


@pytest.mark.parametrize(
    "params",
    [None, {}, {"app_types": "app_security"}],
)
async def test_handle_error_without_home_id_keeps_message_unchanged(auth, params):
    """A request carrying no home id logs and raises exactly as it did before."""
    resp = MockResponse({"error": {"code": 2, "message": "Invalid access token"}}, 400)

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 400, "https://x/y", params=params)

    message = str(exc_info.value)
    assert "for home" not in message
    assert message.endswith("when accessing 'https://x/y'")


async def test_handle_error_unparsable_body_names_the_home(auth):
    """The fallback message for an unreadable body also names the home."""
    resp = _UnparsableResponse(ContentTypeError(None, ()))

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(
            resp,
            400,
            "https://x/homestatus",
            params={"home_id": "5ed02c730474377f3443794a"},
        )

    assert "for home 5ed02c730474377f3443794a" in str(exc_info.value)


async def test_process_response_logs_the_home_id(auth, caplog):
    """The debug line names the home the failed request was for."""
    resp = MockResponse({"error": {"code": 21, "message": "Invalid home_id"}}, 400)

    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.auth"),
        pytest.raises(InvalidHomeError),
    ):
        await auth.process_response(
            resp,
            "https://x/homestatus",
            params={"home_id": "5ed02c730474377f3443794a"},
        )

    assert "for home 5ed02c730474377f3443794a" in caplog.text


async def test_process_response_log_unchanged_without_home_id(auth, caplog):
    """Without a home id the debug line carries no empty 'for home' noise."""
    resp = MockResponse({"error": {"code": 2, "message": "nope"}}, 400)

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"), pytest.raises(ApiError):
        await auth.process_response(resp, "https://x/y")

    assert "The Netatmo API returned" in caplog.text
    assert "for home" not in caplog.text


async def test_error_path_never_leaks_the_webhook_url(auth, caplog):
    """Only the home id is taken from params - the webhook_id stays secret.

    async_post_request also carries ``params={"url": ...}`` for webhook
    registration, and that URL embeds the secret webhook_id.
    """
    webhook_url = "https://hass.example/api/webhook/s3cr3t-webhook-id"
    resp = MockResponse({"error": {"code": 2, "message": "nope"}}, 400)

    with (
        caplog.at_level(logging.DEBUG, logger="pyatmo.auth"),
        pytest.raises(ApiError) as exc_info,
    ):
        await auth.process_response(
            resp,
            "https://x/addwebhook",
            params={"url": webhook_url},
        )

    assert "s3cr3t-webhook-id" not in str(exc_info.value)
    assert "s3cr3t-webhook-id" not in caplog.text


async def test_post_request_passes_params_to_the_error_path():
    """The POST transport hands its params to the shared error handling."""

    class _Session:
        def post(self, _url, **_kwargs):
            return MockResponse(
                {"error": {"code": 21, "message": "Invalid home_id"}},
                400,
            )

    auth = _Auth(websession=_Session())

    with pytest.raises(InvalidHomeError) as exc_info:
        await auth.async_post_request(
            "https://x/api/homestatus",
            params={"home_id": "5ed02c730474377f3443794a"},
        )

    assert "for home 5ed02c730474377f3443794a" in str(exc_info.value)


async def test_get_request_passes_params_to_the_error_path():
    """The GET transport hands its params to the shared error handling."""

    class _Session:
        def get(self, _url, **_kwargs):
            return MockResponse(
                {"error": {"code": 21, "message": "Invalid home_id"}},
                400,
            )

    auth = _Auth(websession=_Session())

    with pytest.raises(InvalidHomeError) as exc_info:
        await auth.async_get_request(
            "https://x/api/homestatus",
            params={"home_id": "5ed02c730474377f3443794a"},
        )

    assert "for home 5ed02c730474377f3443794a" in str(exc_info.value)
