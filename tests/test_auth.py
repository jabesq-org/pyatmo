"""Tests for pyatmo.auth retry / 429 concurrency handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from json import JSONDecodeError
import logging
from urllib.parse import quote, urlencode, urlsplit

from aiohttp import ContentTypeError
import pytest
from tenacity import Future, RetryCallState

from pyatmo.auth import (
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RETRIES,
    MAX_RETRY_AFTER,
    REDACTED_TAIL_LENGTH,
    AbstractAsyncAuth,
    _parse_retry_after,
    _redact_webhook_url,
    _wait_retry_after,
)
from pyatmo.const import CONCURRENCY_ERROR_CODE, THROTTLING_ERROR_CODE
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


@pytest.mark.parametrize("cls", [ApiError, ApiTooManyRequestError])
def test_api_error_constructs_without_arguments(cls):
    """Every argument stays optional, as before status and code existed.

    These are public exception classes that used to inherit
    ``Exception.__init__``, so downstream code may construct them bare.
    """
    err = cls()

    assert str(err) == ""
    assert err.status is None
    assert err.code is None


def test_api_error_carries_status_and_code():
    """Both are exposed for a caller that must tell one error code apart."""
    err = ApiError("boom", status=400, code=21)

    assert str(err) == "boom"
    assert err.status == 400
    assert err.code == 21


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
    """The scheme and host survive; all but the last few secret chars do not.

    The host distinguishes a Nabu Casa cloudhook from a self-hosted endpoint,
    and the short tail lets a reader tell two webhooks apart and follow one
    across log lines. The tail is a deliberate, bounded exception -- nothing
    beyond REDACTED_TAIL_LENGTH characters may ever reach a log.
    """
    redacted = _redact_webhook_url(FAKE_CLOUDHOOK)

    assert redacted == "https://hooks.nabu.casa/...9Qb="
    for length in range(REDACTED_TAIL_LENGTH + 1, len(FAKE_SECRET) + 1):
        assert FAKE_SECRET[-length:] not in redacted


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


@pytest.mark.parametrize(
    "value",
    [
        "https://ha:Passw0rd@ha.example.org/api/webhook/abcdefghij",
        "https://ha:Passw0rd@ha.example.org:8123/api/webhook/abcdefghij",
        "https://token@ha.example.org/api/webhook/abcdefghij",
    ],
)
def test_redact_webhook_url_drops_userinfo(value):
    """Credentials in the authority must never reach a log.

    urlsplit keeps userinfo in netloc, so rendering the netloc verbatim
    would publish the password of anyone fronting Home Assistant with a
    basic-auth reverse proxy.
    """
    redacted = _redact_webhook_url(value)

    # Parsed rather than prefix-matched: startswith would also accept
    # "https://ha.example.org.evil.test/", so it does not pin the host.
    parsed = urlsplit(redacted)

    assert parsed.scheme == "https"
    assert parsed.hostname == "ha.example.org"
    assert parsed.username is None
    assert parsed.password is None
    assert "Passw0rd" not in redacted
    assert "token" not in redacted


# The transport method each verb reaches, so a stub can replace one by name.
_TRANSPORT = {
    "get": "async_get_request",
    "post": "async_post_request",
    "delete": "async_delete_request",
}


def _stub(auth, verb, payload=None, exc=None):
    """Replace one auth transport with a stub, returning the kwargs it saw.

    The returned dict is updated in place on every call, so a test reads it
    after awaiting the code under test. Use ``_stub_sequence`` instead when the
    call count matters or successive calls must answer differently.
    """
    seen = {}

    async def fake_request(*_args, **kwargs):
        seen.update(kwargs)
        if exc is not None:
            raise exc
        return MockResponse({"status": "ok"} if payload is None else payload, 200)

    setattr(auth, _TRANSPORT[verb], fake_request)
    return seen


def _stub_sequence(auth, verb, results):
    """Return each result in turn: an exception is raised, else a response.

    Every call is recorded separately, unlike ``_stub``, so a test can assert
    how many times the transport was reached and with what.
    """
    calls = []

    async def fake_request(*_args, **kwargs):
        calls.append(kwargs)
        result = results[len(calls) - 1]
        if isinstance(result, Exception):
            raise result
        return result

    setattr(auth, _TRANSPORT[verb], fake_request)
    return calls


async def test_list_webhooks_returns_registered_url(auth):
    """A registered webhook is returned as a single-entry list."""
    _stub(auth, "get", {"status": "ok", "body": [{"url": "https://example.com/hook"}]})

    assert await auth.async_list_webhooks() == ["https://example.com/hook"]


async def test_list_webhooks_hits_expected_url(auth):
    """The listing endpoint is appended to the base URL without an api/ prefix."""
    seen = _stub(auth, "get", {"status": "ok", "body": []})

    await auth.async_list_webhooks()

    assert seen["url"] == "https://api.netatmo.com/webhooks/v1"


async def test_list_webhooks_empty_body(auth):
    """No registered webhook yields an empty list."""
    _stub(auth, "get", {"status": "ok", "body": []})

    assert await auth.async_list_webhooks() == []


async def test_list_webhooks_multiple_urls_in_order(auth):
    """Several registered webhooks are all returned, in payload order."""
    _stub(
        auth,
        "get",
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
    _stub(auth, "get", payload)

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
    _stub(
        auth,
        "get",
        {"status": "ok", "body": [entry, {"url": "https://example.com/hook"}]},
    )

    with pytest.raises(ApiError, match="Unexpected webhook entry"):
        await auth.async_list_webhooks()


async def test_list_webhooks_error_message_omits_urls(auth):
    """A malformed entry is reported by its keys, never its values.

    A webhook URL is a capability URL; it must not reach an exception message.
    """
    _stub(
        auth,
        "get",
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
    _stub(auth, "get", exc=ApiError(boom))

    with pytest.raises(ApiError, match=boom):
        await auth.async_list_webhooks()


async def test_list_webhooks_timeout_raises_api_error(auth):
    """A TimeoutError surfaces as ApiError, like the add/drop helpers."""
    _stub(auth, "get", exc=TimeoutError)

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
    _stub(auth, "get", {"status": "ok", "body": [{"url": FAKE_CLOUDHOOK}]})

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"):
        await auth.async_list_webhooks()

    assert FAKE_SECRET not in caplog.text
    for length in range(REDACTED_TAIL_LENGTH + 1, len(FAKE_SECRET) + 1):
        assert FAKE_SECRET[-length:] not in caplog.text
    assert "list_webhooks: 1 registered" in caplog.text
    assert "https://hooks.nabu.casa/...9Qb=" in caplog.text


async def test_list_webhooks_debug_log_counts_every_url(auth, caplog):
    """The count is the useful part, and it stays truthful for several hooks."""
    _stub(
        auth,
        "get",
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
    _stub(auth, "get", {"status": "ok", "body": []})

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
        query = kwargs.get("params") or {}
        rendered = f"{url}?{urlencode(query)}" if query else url
        return _ReprResponse(rendered)


async def test_addwebhook_sends_the_url_in_the_body_not_the_query():
    """The registration URL must stay out of the request URL.

    A webhook URL is a capability URL - possession of it is the whole
    credential. ``async_addwebhook`` finishes with ``LOG.debug("addwebhook:
    %s", resp)``, and an aiohttp ``ClientResponse`` repr renders the *request*
    URL, so that debug line is only safe while the webhook URL travels in the
    JSON body. Moving it to ``params`` would put it in the query string, the
    response repr and every debug log from there on.

    ``test_addwebhook_debug_log_does_not_leak_the_url`` does not cover this:
    ``_RecordingSession.post`` builds its ``_ReprResponse`` from the bare
    ``url`` argument, so a regression to ``params={"url": ...}`` would still
    leave that test green.
    """
    session = _RecordingSession()
    auth = _Auth(websession=session)

    await auth.async_addwebhook(FAKE_CLOUDHOOK)

    assert session.seen["url"] == "https://api.netatmo.com/webhooks/v1"
    assert session.seen["json"] == {"url": FAKE_CLOUDHOOK}
    assert "params" not in session.seen
    assert "data" not in session.seen
    assert FAKE_SECRET not in session.seen["url"]


async def test_addwebhook_debug_log_does_not_leak_the_url(caplog):
    """The addwebhook debug line renders a response, never the registered URL."""
    auth = _Auth(websession=_RecordingSession())

    with caplog.at_level(logging.DEBUG, logger="pyatmo.auth"):
        await auth.async_addwebhook(FAKE_CLOUDHOOK)

    assert FAKE_SECRET not in caplog.text
    # Percent-encoded too: a URL smuggled into the query string reaches the
    # response repr with its "=" as "%3D", so the raw secret would not match.
    assert quote(FAKE_SECRET, safe="") not in caplog.text
    assert FAKE_SECRET.rstrip("=") not in caplog.text
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
    assert seen["url"] == "https://api.netatmo.com/webhooks/v1"
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


async def test_handle_error_400_code_21_stays_generic(auth):
    """400 + code 21 is a plain ApiError carrying the code.

    Code 21 is a generic invalid-parameter code, not "invalid home id": the
    auth layer sees only a status, a code and a URL, so it cannot know what the
    caller asked for. Translating it is the caller's job.
    """
    resp = MockResponse({"error": {"code": 21, "message": "Invalid home_id"}}, 400)

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 400, "https://x/y")

    assert not isinstance(exc_info.value, InvalidHomeError)
    assert exc_info.value.code == 21


async def test_addwebhook_rejected_url_is_not_an_invalid_home():
    """A URL Netatmo refuses must not surface as a rejected home.

    The legacy ``api/addwebhook`` answered a URL whose host does not resolve
    with the very same ``400`` + code 21 that ``/homestatus`` answers a
    rejected home id with (both measured 2026-08-14, against the legacy
    endpoint; whether ``POST webhooks/v1`` rejects an unresolvable host the
    same way is assumed, not measured). What this pins does not depend on that:
    code 21 must not become ``InvalidHomeError`` anywhere, and that pairing is
    still reachable from ``/homestatus``. A consumer acting on
    ``InvalidHomeError`` would stop polling a perfectly good home because of a
    webhook registration mistake.
    """

    class _Session:
        def post(self, _url, **_kwargs):
            return MockResponse(
                {"error": {"code": 21, "message": "Invalid url parameter"}},
                400,
            )

    auth = _Auth(websession=_Session())

    with pytest.raises(ApiError) as exc_info:
        await auth.async_addwebhook("https://does-not-resolve.invalid/hook")

    assert not isinstance(exc_info.value, InvalidHomeError)
    assert exc_info.value.code == 21


async def test_handle_error_exposes_status_and_code(auth):
    """The exception carries what the caller needs to interpret the failure."""
    resp = MockResponse({"error": {"code": 21, "message": "Invalid home_id"}}, 400)

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 400, "https://x/y")

    assert exc_info.value.status == 400
    assert exc_info.value.code == 21


async def test_handle_error_unparsable_body_exposes_status_without_code(auth):
    """An unreadable body yields the status it came with and no code."""
    resp = _UnparsableResponse(ContentTypeError(None, ()))

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 400, "https://x/y")

    assert exc_info.value.status == 400
    assert exc_info.value.code is None


async def test_handle_error_409_string_code_renders_the_status_name(auth):
    """A ``webhooks/v1`` conflict renders a complete message and keeps its code.

    ``POST webhooks/v1`` answers a second registration with ``409`` and a
    *string* code (measured 2026-08-15). Without a 409 entry in ``ERRORS`` the
    message rendered with an empty middle field.
    """
    resp = MockResponse(
        {"error": {"code": "WH009", "message": "webhook limit reached"}},
        409,
    )

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 409, "https://x/y")

    assert "409 - Conflict - webhook limit reached (WH009)" in str(exc_info.value)
    assert exc_info.value.status == 409
    assert exc_info.value.code == "WH009"


async def test_handle_error_string_code_never_matches_an_integer_code(auth):
    """A string code must not be mistaken for one of the integer codes.

    The auth layer branches on ``code == 11`` / ``code == 26``; a string code
    equals neither, so the generic ``ApiError`` is raised and the code reaches
    the caller unconverted.
    """
    resp = MockResponse(
        {"error": {"code": "WH009", "message": "webhook limit reached"}},
        429,
    )

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 429, "https://x/y")

    assert not isinstance(exc_info.value, ApiTooManyRequestError)
    assert "429 - Too Many Requests - " in str(exc_info.value)
    assert exc_info.value.code == "WH009"
    assert exc_info.value.code != CONCURRENCY_ERROR_CODE


async def test_handle_error_403_string_code_is_not_throttling(auth):
    """The 403 branch is likewise keyed on the integer code 26."""
    resp = MockResponse({"error": {"code": "WH001", "message": "nope"}}, 403)

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 403, "https://x/y")

    assert not isinstance(exc_info.value, ApiThrottlingError)
    assert exc_info.value.code == "WH001"
    assert exc_info.value.code != THROTTLING_ERROR_CODE


async def test_handle_error_400_without_code_21_stays_generic(auth):
    """Any other 400 is an ApiError too - no error code is special-cased here."""
    resp = MockResponse({"error": {"code": 2, "message": "Invalid access token"}}, 400)

    with pytest.raises(ApiError):
        await auth.handle_error_response(resp, 400, "https://x/y")


async def test_handle_error_names_the_home_from_params(auth):
    """The rejected home id reaches the exception message.

    The home id travels in the POST body, not the URL, so without this a
    consumer cannot tell which of its homes the API rejected.
    """
    resp = MockResponse({"error": {"code": 21, "message": "Invalid home_id"}}, 400)

    with pytest.raises(ApiError) as exc_info:
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
        pytest.raises(ApiError),
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

    with pytest.raises(ApiError) as exc_info:
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

    with pytest.raises(ApiError) as exc_info:
        await auth.async_get_request(
            "https://x/api/homestatus",
            params={"home_id": "5ed02c730474377f3443794a"},
        )

    assert "for home 5ed02c730474377f3443794a" in str(exc_info.value)


class _FakeDeleteSession:
    """Minimal websession recording the delete call it received.

    ``MockResponse`` is itself an async context manager (``tests/common.py``),
    so it can be returned straight from ``delete()``.
    """

    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.seen = {}

    def delete(self, url, **kwargs):
        self.seen = {"url": url, **kwargs}
        return MockResponse(self.payload, self.status)


async def test_delete_request_issues_a_delete_with_the_bearer_token():
    """A DELETE carries the access token and reaches the given url."""
    session = _FakeDeleteSession({"status": "ok"})
    auth = _Auth(websession=session)

    await auth.async_delete_request(url="https://api.netatmo.com/webhooks/v1")

    assert session.seen["url"] == "https://api.netatmo.com/webhooks/v1"
    assert session.seen["headers"]["Authorization"] == "Bearer token"


async def test_delete_api_request_appends_the_endpoint_to_the_base_url():
    """The endpoint is joined to the base url, as the get wrapper does."""
    session = _FakeDeleteSession({"status": "ok"})
    auth = _Auth(websession=session)

    await auth.async_delete_api_request(endpoint="webhooks/v1")

    assert session.seen["url"] == "https://api.netatmo.com/webhooks/v1"


async def test_delete_request_raises_api_error_on_error_status():
    """A DELETE goes through the same error handling as every other verb."""
    session = _FakeDeleteSession({"error": {"code": "WH404", "message": "nope"}}, 404)
    auth = _Auth(websession=session)

    with pytest.raises(ApiError) as exc_info:
        await auth.async_delete_request(url="https://api.netatmo.com/webhooks/v1")

    assert exc_info.value.status == 404
    assert exc_info.value.code == "WH404"


async def test_delete_api_request_retries_then_succeeds(auth):
    """A transient 429/code-11 on the DELETE path is retried, then succeeds.

    ``DELETE /webhooks/v1`` takes no body and clears the application's single
    webhook, so repeating it converges on the same state - retrying is safe on
    the merits, not merely for symmetry with the get and post wrappers.
    """
    success = MockResponse({"status": "ok"}, 200)
    calls = 0
    busy = "busy"

    async def flaky(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ApiTooManyRequestError(busy, retry_after=0.0)
        return success

    auth.async_delete_request = flaky

    result = await auth.async_delete_api_request(endpoint="webhooks/v1")

    assert result is success
    assert calls == 3


async def test_dropwebhook_issues_a_delete_to_webhooks_v1(auth):
    """Unregistering uses DELETE, not a post to the legacy endpoint."""
    seen = _stub(auth, "delete")

    await auth.async_dropwebhook()

    assert seen["url"] == "https://api.netatmo.com/webhooks/v1"


async def test_dropwebhook_sends_no_app_types_parameter(auth):
    """The legacy app_types parameter has no meaning on the v1 endpoint."""
    seen = _stub(auth, "delete")

    await auth.async_dropwebhook()

    assert seen.get("params") is None


async def test_dropwebhook_timeout_raises_api_error(auth):
    """A timeout is still reported as an ApiError, as before."""
    _stub(auth, "delete", exc=TimeoutError)

    with pytest.raises(ApiError, match="timed out"):
        await auth.async_dropwebhook()


async def test_addwebhook_posts_json_to_webhooks_v1(auth):
    """Nothing registered: a single POST with a JSON body."""
    posted = _stub(auth, "post")

    await auth.async_addwebhook("https://example.com/hook")

    assert posted["url"] == "https://api.netatmo.com/webhooks/v1"
    assert posted["params"] == {"json": {"url": "https://example.com/hook"}}


async def test_addwebhook_surfaces_a_failure_after_the_delete_succeeded(auth):
    """A retry POST that fails after a successful delete reaches the caller unchanged.

    Nothing is rolled back: the old registration is gone and the new one was
    never made. A plain retry then finds nothing registered, so its first POST
    succeeds and the call self-heals.
    """
    conflict = ApiError("409 - Conflict - limit (WH009)", status=409, code="WH009")
    failure = ApiError("400 - Bad Request - nope (21)", status=400, code=21)
    posts = _stub_sequence(auth, "post", [conflict, failure])
    deleted = _stub(auth, "delete")

    with pytest.raises(ApiError) as exc_info:
        await auth.async_addwebhook("https://example.com/hook")

    assert deleted["url"] == "https://api.netatmo.com/webhooks/v1"
    assert len(posts) == 2
    assert exc_info.value.code == 21


async def test_addwebhook_delete_timeout_does_not_claim_registration_timed_out(auth):
    """A timeout removing the incumbent must not be reported as a registration one.

    The retry registration was never attempted, and the delete may well have
    gone through - so the caller may have been left with no webhook at all, the
    opposite of what "registration timed out" implies.
    """
    conflict = ApiError("409 - Conflict - limit (WH009)", status=409, code="WH009")
    posts = _stub_sequence(auth, "post", [conflict])
    _stub(auth, "delete", exc=TimeoutError)

    with pytest.raises(ApiError) as exc_info:
        await auth.async_addwebhook("https://example.com/hook")

    message = str(exc_info.value).lower()
    assert "timed out" in message
    assert "removal" in message
    assert "registration timed out" not in message
    assert len(posts) == 1


async def test_addwebhook_timeout_raises_api_error(auth):
    """A timeout is still reported as an ApiError, as before.

    The POST is the step that names registration - the removal reports its own
    timeout, so a caller can tell the two apart.
    """
    _stub(auth, "post", exc=TimeoutError)

    with pytest.raises(ApiError, match="registration timed out"):
        await auth.async_addwebhook("https://example.com/hook")


async def test_addwebhook_registers_without_listing_first(auth):
    """Nothing registered: one POST, and the listing is never consulted."""
    listed = _stub(auth, "get", {"status": "ok", "body": []})
    posted = _stub(auth, "post")

    await auth.async_addwebhook("https://example.com/hook")

    assert posted["params"] == {"json": {"url": "https://example.com/hook"}}
    assert listed == {}


async def test_addwebhook_clears_and_retries_on_conflict(auth):
    """409 means one is already registered: clear it, then register again."""
    conflict = ApiError("409 - Conflict - limit (WH009)", status=409, code="WH009")
    posts = _stub_sequence(
        auth, "post", [conflict, MockResponse({"status": "ok"}, 200)]
    )
    deleted = _stub(auth, "delete")

    await auth.async_addwebhook("https://example.com/hook")

    assert len(posts) == 2
    assert deleted["url"] == "https://api.netatmo.com/webhooks/v1"
    assert posts[1]["params"] == {"json": {"url": "https://example.com/hook"}}


async def test_addwebhook_re_registers_the_same_url(auth):
    """Re-registering an unchanged URL is NOT a no-op.

    The listing reports deliverable hooks, not registered ones, so a hook
    Netatmo has stopped delivering to still has to be cleared and posted
    again -- that is the only way to re-arm it.
    """
    conflict = ApiError("409 - Conflict - limit (WH009)", status=409, code="WH009")
    posts = _stub_sequence(
        auth, "post", [conflict, MockResponse({"status": "ok"}, 200)]
    )
    deleted = _stub(auth, "delete")

    await auth.async_addwebhook("https://example.com/hook")

    assert len(posts) == 2
    assert deleted != {}


async def test_addwebhook_does_not_retry_a_second_conflict(auth):
    """A conflict surviving the removal is surfaced, not retried forever."""
    conflict = ApiError("409 - Conflict - limit (WH009)", status=409, code="WH009")
    posts = _stub_sequence(auth, "post", [conflict, conflict])
    _stub(auth, "delete")

    with pytest.raises(ApiError) as exc_info:
        await auth.async_addwebhook("https://example.com/hook")

    assert exc_info.value.status == 409
    assert len(posts) == 2


async def test_addwebhook_surfaces_a_non_conflict_error(auth):
    """Any other error propagates without touching the registration."""
    _stub(auth, "post", exc=ApiError("400 - Bad request", status=400, code=21))
    deleted = _stub(auth, "delete")

    with pytest.raises(ApiError) as exc_info:
        await auth.async_addwebhook("https://example.com/hook")

    assert exc_info.value.status == 400
    assert deleted == {}


async def test_handle_error_names_the_home_from_a_json_body(auth):
    """Write endpoints nest the home id in the JSON body, not the params."""
    resp = MockResponse({"error": {"code": 7, "message": "nope"}}, 500)
    params = {"json": {"home": {"id": "5ed02c730474377f3443794a", "foo": "bar"}}}

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(resp, 500, "https://x/y", params=params)

    assert "for home 5ed02c730474377f3443794a" in str(exc_info.value)


async def test_handle_error_json_body_without_a_home_is_unchanged(auth):
    """A JSON body carrying no home adds no suffix."""
    resp = MockResponse({"error": {"code": 7, "message": "nope"}}, 500)

    with pytest.raises(ApiError) as exc_info:
        await auth.handle_error_response(
            resp,
            500,
            "https://x/y",
            params={"json": {"url": "https://example.com/hook"}},
        )

    assert "for home" not in str(exc_info.value)
    assert "example.com" not in str(exc_info.value)


async def test_too_many_request_error_carries_status_and_code(auth):
    """The retryable errors carry the discriminator too, not just ApiError."""
    resp = MockResponse({"error": {"code": 11, "message": "concurrency"}}, 429)

    with pytest.raises(ApiTooManyRequestError) as exc_info:
        await auth.handle_error_response(resp, 429, "https://x/y")

    assert exc_info.value.status == 429
    assert exc_info.value.code == 11


async def test_throttling_error_carries_status_and_code(auth):
    """Same for the 403 throttling case."""
    resp = MockResponse({"error": {"code": 26, "message": "throttled"}}, 403)

    with pytest.raises(ApiThrottlingError) as exc_info:
        await auth.handle_error_response(resp, 403, "https://x/y")

    assert exc_info.value.status == 403
    assert exc_info.value.code == 26
