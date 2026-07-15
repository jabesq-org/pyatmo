"""Tests for pyatmo.auth retry / 429 concurrency handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest
from tenacity import Future, RetryCallState

from pyatmo.auth import (
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RETRIES,
    MAX_RETRY_AFTER,
    AbstractAsyncAuth,
    _parse_retry_after,
    _wait_retry_after,
)
from pyatmo.exceptions import ApiError, ApiThrottlingError, ApiTooManyRequestError

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
