"""Support for Netatmo authentication."""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from json import JSONDecodeError
from time import sleep
from typing import Any, Callable

import requests
from aiohttp import ClientError, ClientResponse, ClientSession
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError
from requests_oauthlib import OAuth2Session

from pyatmo.const import (
    ALL_SCOPES,
    AUTH_REQ_ENDPOINT,
    AUTH_URL_ENDPOINT,
    AUTHORIZATION_HEADER,
    DEFAULT_BASE_URL,
    ERRORS,
    WEBHOOK_URL_ADD_ENDPOINT,
    WEBHOOK_URL_DROP_ENDPOINT,
)
from pyatmo.exceptions import ApiError

LOG = logging.getLogger(__name__)


class NetatmoOAuth2:
    """
    Handle authentication with OAuth2
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str | None = None,
        token: dict[str, str] | None = None,
        token_updater: Callable[[str], None] | None = None,
        scope: str | None = "read_station",
        user_prefix: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Initialize self.

        Keyword Arguments:
            client_id {str} -- Application client ID delivered by Netatmo on dev.netatmo.com (default: {None})
            client_secret {str} -- Application client secret delivered by Netatmo on dev.netatmo.com (default: {None})
            redirect_uri {Optional[str]} -- Redirect URI where to the authorization server will redirect with an authorization code (default: {None})
            token {Optional[Dict[str, str]]} -- Authorization token (default: {None})
            token_updater {Optional[Callable[[str], None]]} -- Callback when the token is updated (default: {None})
            scope {Optional[str]} -- List of scopes (default: {"read_station"})
                read_station: to retrieve weather station data (Getstationsdata, Getmeasure)
                read_camera: to retrieve Welcome data (Gethomedata, Getcamerapicture)
                access_camera: to access the camera, the videos and the live stream
                write_camera: to set home/away status of persons (Setpersonsaway, Setpersonshome)
                read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
                write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
                read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
                access_presence: to access the live stream, any video stored on the SD card and to retrieve Presence's lightflood status
                read_homecoach: to retrieve Home Coache data (Gethomecoachsdata)
                read_smokedetector: to retrieve the smoke detector status (Gethomedata)
                Several values can be used at the same time, ie: 'read_station read_camera'
            user_prefix {Optional[str]} -- API prefix for the Netatmo customer
            base_url {str} -- Base URL of the Netatmo API (default: {_DEFAULT_BASE_URL})
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_updater = token_updater
        self.user_prefix = user_prefix
        self.base_url = base_url

        if token:
            self.scope = " ".join(token["scope"])

        else:
            self.scope = scope or " ".join(ALL_SCOPES)

        self.extra = {"client_id": self.client_id, "client_secret": self.client_secret}

        self._oauth = OAuth2Session(
            client_id=self.client_id,
            token=token,
            token_updater=self.token_updater,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
        )

    def refresh_tokens(self) -> Any:
        """Refresh and return new tokens."""
        token = self._oauth.refresh_token(
            self.base_url + AUTH_REQ_ENDPOINT,
            **self.extra,
        )

        if self.token_updater is not None:
            self.token_updater(token)

        return token

    def post_api_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: int = 5,
    ) -> requests.Response:
        return self.post_request(
            url=self.base_url + endpoint,
            params=params,
            timeout=timeout,
        )

    def post_request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: int = 5,
    ) -> requests.Response:
        """Wrapper for post requests."""
        resp = None
        req_args = {"data": params if params is not None else {}}

        if "json" in req_args["data"]:
            req_args["json"] = req_args["data"]["json"]
            req_args.pop("data")

        if "https://" not in url:
            try:
                resp = requests.post(url, data=params, timeout=timeout)
            except requests.exceptions.ChunkedEncodingError:
                LOG.debug("Encoding error when connecting to '%s'", url)
            except requests.exceptions.ConnectTimeout:
                LOG.debug("Connection to %s timed out", url)
            except requests.exceptions.ConnectionError:
                LOG.debug("Remote end closed connection without response (%s)", url)

        else:

            def query(
                url: str,
                params: dict[str, Any],
                timeout: int,
                retries: int,
            ) -> Any:
                if retries == 0:
                    LOG.error("Too many retries")
                    return requests.Response()

                try:
                    return self._oauth.post(url=url, timeout=timeout, **params)

                except (
                    TokenExpiredError,
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectionError,
                ):
                    self._oauth.token = self.refresh_tokens()
                    # Sleep for 1 sec to prevent authentication related
                    # timeouts after a token refresh.
                    sleep(1)
                    return query(url, params, timeout * 2, retries - 1)

            resp = query(url, req_args, timeout, 3)

        if resp is None:
            LOG.debug("Resp is None - %s", resp)
            return requests.Response()

        if not resp.ok:
            LOG.debug(
                "The Netatmo API returned %s (%s)",
                resp.content,
                resp.status_code,
            )
            try:
                raise ApiError(
                    f"{resp.status_code} - "
                    f"{ERRORS.get(resp.status_code, '')} - "
                    f"{resp.json()['error']['message']} "
                    f"({resp.json()['error']['code']}) "
                    f"when accessing '{url}'",
                )

            except JSONDecodeError as exc:
                raise ApiError(
                    f"{resp.status_code} - "
                    f"{ERRORS.get(resp.status_code, '')} - "
                    f"when accessing '{url}'",
                ) from exc

        if "application/json" in resp.headers.get(
            "content-type",
            [],
        ) or resp.content not in [b"", b"None"]:
            return resp

        return requests.Response()

    def get_authorization_url(self, state: str | None = None) -> Any:
        return self._oauth.authorization_url(self.base_url + AUTH_URL_ENDPOINT, state)

    def request_token(
        self,
        authorization_response: str | None = None,
        code: str | None = None,
    ) -> Any:
        """
        Generic method for fetching a Netatmo access token.
        :param authorization_response: Authorization response URL, the callback URL of the request back to you.
        :param code: Authorization code.
        :return: A token dict.
        """
        return self._oauth.fetch_token(
            self.base_url + AUTH_REQ_ENDPOINT,
            authorization_response=authorization_response,
            code=code,
            client_secret=self.client_secret,
            include_client_id=True,
            user_prefix=self.user_prefix,
        )

    def addwebhook(self, webhook_url: str) -> None:
        post_params = {"url": webhook_url}
        resp = self.post_api_request(WEBHOOK_URL_ADD_ENDPOINT, post_params)
        LOG.debug("addwebhook: %s", resp)

    def dropwebhook(self) -> None:
        post_params = {"app_types": "app_security"}
        resp = self.post_api_request(WEBHOOK_URL_DROP_ENDPOINT, post_params)
        LOG.debug("dropwebhook: %s", resp)


class ClientAuth(NetatmoOAuth2):
    """
    Request authentication and keep access token available through token method. Renew it automatically if necessary
    Args:
        clientId (str): Application clientId delivered by Netatmo on dev.netatmo.com
        clientSecret (str): Application Secret key delivered by Netatmo on dev.netatmo.com
        username (str)
        password (str)
        scope (Optional[str]):
            read_station: to retrieve weather station data (Getstationsdata, Getmeasure)
            read_camera: to retrieve Welcome data (Gethomedata, Getcamerapicture)
            access_camera: to access the camera, the videos and the live stream
            write_camera: to set home/away status of persons (Setpersonsaway, Setpersonshome)
            read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
            write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
            read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
            access_presence: to access the live stream, any video stored on the SD card and to retrieve Presence's lightflood status
            read_homecoach: to retrieve Home Coache data (Gethomecoachsdata)
            read_smokedetector: to retrieve the smoke detector status (Gethomedata)
            Several value can be used at the same time, ie: 'read_station read_camera'
        user_prefix (Optional[str]) -- API prefix for the Netatmo customer
        base_url (str) -- Base URL of the Netatmo API (default: {_DEFAULT_BASE_URL})
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        scope: str = "read_station",
        user_prefix: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            user_prefix=user_prefix,
            base_url=base_url,
        )

        self._oauth = OAuth2Session(
            client=LegacyApplicationClient(client_id=self.client_id),
        )
        self._oauth.fetch_token(
            token_url=self.base_url + AUTH_REQ_ENDPOINT,
            username=username,
            password=password,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=self.scope,
            user_prefix=self.user_prefix,
        )


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
        """Wrapper for async get requests."""
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
            resp_status = resp.status
            resp_content = await resp.read()

            if resp.headers.get("content-type") == "image/jpeg":
                return resp_content

        raise ApiError(
            f"{resp_status} - "
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
        """Wrapper for async post requests."""
        try:
            access_token = await self.async_get_access_token()
        except ClientError as err:
            raise ApiError(f"Access token failure: {err}") from err
        headers = {AUTHORIZATION_HEADER: f"Bearer {access_token}"}

        req_args = {"data": params if params is not None else {}}

        if "json" in req_args["data"]:
            req_args["json"] = req_args["data"]["json"]
            req_args.pop("data")

        async with self.websession.post(
            url,
            **req_args,
            headers=headers,
            timeout=timeout,
        ) as resp:
            resp_status = resp.status
            resp_content = await resp.read()

            if not resp.ok:
                LOG.debug("The Netatmo API returned %s (%s)", resp_content, resp_status)
                try:
                    resp_json = await resp.json()
                    raise ApiError(
                        f"{resp_status} - "
                        f"{ERRORS.get(resp_status, '')} - "
                        f"{resp_json['error']['message']} "
                        f"({resp_json['error']['code']}) "
                        f"when accessing '{url}'",
                    )

                except JSONDecodeError as exc:
                    raise ApiError(
                        f"{resp_status} - "
                        f"{ERRORS.get(resp_status, '')} - "
                        f"when accessing '{url}'",
                    ) from exc

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
