"""Support for Netatmo authentication."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from json import JSONDecodeError
import logging
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ContentTypeError

from pyatmo.const import (
    AUTHORIZATION_HEADER,
    DEFAULT_BASE_URL,
    ERRORS,
    WEBHOOK_URL_ADD_ENDPOINT,
    WEBHOOK_URL_DROP_ENDPOINT,
)
from pyatmo.exceptions import ApiError

LOG = logging.getLogger(__name__)


class AbstractAsyncAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(
        self,
        websession: ClientSession,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Initialize the auth."""

        self.websession = websession
        self.base_url = base_url

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def async_get_image(
        self,
        endpoint: str,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 5,
    ) -> bytes:
        """Wrap async get requests."""

        try:
            access_token = await self.async_get_access_token()
        except ClientError as err:
            raise ApiError(f"Access token failure: {err}") from err
        headers = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        req_args = {"data": params if params is not None else {}}

        url = (base_url or self.base_url) + endpoint
        async with self.websession.get(
            url,
            **req_args,  # type: ignore
            headers=headers,
            timeout=timeout,
        ) as resp:
            resp_content = await resp.read()

            if resp.headers.get("content-type") == "image/jpeg":
                return resp_content

        raise ApiError(
            f"{resp.status} - "
            f"invalid content-type in response"
            f"when accessing '{url}'",
        )

    async def async_post_api_request(
        self,
        endpoint: str,
        base_url: str | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 5,
    ) -> ClientResponse:
        """Wrap async post requests."""

        return await self.async_post_request(
            url=(base_url or self.base_url) + endpoint,
            params=params,
            timeout=timeout,
        )

    async def async_post_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: int = 5,
    ) -> ClientResponse:
        """Wrap async post requests."""

        access_token = await self.get_access_token()
        headers = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        req_args = self.prepare_request_arguments(params)

        async with self.websession.post(
            url,
            **req_args,
            headers=headers,
            timeout=timeout,
        ) as resp:
            return await self.process_response(resp, url)

    async def get_access_token(self):
        """Get access token."""
        try:
            return await self.async_get_access_token()
        except ClientError as err:
            raise ApiError(f"Access token failure: {err}") from err

    def prepare_request_arguments(self, params):
        """Prepare request arguments."""
        req_args = {"data": params if params is not None else {}}

        if "params" in req_args["data"]:
            req_args["params"] = req_args["data"]["params"]
            req_args["data"].pop("params")

        if "json" in req_args["data"]:
            req_args["json"] = req_args["data"]["json"]
            req_args.pop("data")

        return req_args

    async def process_response(self, resp, url):
        """Process response."""
        resp_status = resp.status
        resp_content = await resp.read()

        if not resp.ok:
            LOG.debug("The Netatmo API returned %s (%s)", resp_content, resp_status)
            await self.handle_error_response(resp, resp_status, url)

        return await self.handle_success_response(resp, resp_content)

    async def handle_error_response(self, resp, resp_status, url):
        """Handle error response."""
        try:
            resp_json = await resp.json()
            raise ApiError(
                f"{resp_status} - "
                f"{ERRORS.get(resp_status, '')} - "
                f"{resp_json['error']['message']} "
                f"({resp_json['error']['code']}) "
                f"when accessing '{url}'",
            )

        except (JSONDecodeError, ContentTypeError) as exc:
            raise ApiError(
                f"{resp_status} - "
                f"{ERRORS.get(resp_status, '')} - "
                f"when accessing '{url}'",
            ) from exc

    async def handle_success_response(self, resp, resp_content):
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
            resp = await self.async_post_api_request(
                endpoint=WEBHOOK_URL_ADD_ENDPOINT,
                params={"url": webhook_url},
            )
        except asyncio.exceptions.TimeoutError as exc:
            raise ApiError("Webhook registration timed out") from exc
        else:
            LOG.debug("addwebhook: %s", resp)

    async def async_dropwebhook(self) -> None:
        """Unregister webhook."""
        try:
            resp = await self.async_post_api_request(
                endpoint=WEBHOOK_URL_DROP_ENDPOINT,
                params={"app_types": "app_security"},
            )
        except asyncio.exceptions.TimeoutError as exc:
            raise ApiError("Webhook registration timed out") from exc
        else:
            LOG.debug("dropwebhook: %s", resp)
