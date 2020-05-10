import logging
from json import JSONDecodeError
from time import sleep
from typing import Callable, Dict, Optional, Tuple, Union

import requests
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError
from requests_oauthlib import OAuth2Session

from .exceptions import ApiError
from .helpers import _BASE_URL, ERRORS

LOG = logging.getLogger(__name__)

# Common definitions
_AUTH_REQ = _BASE_URL + "oauth2/token"
_AUTH_URL = _BASE_URL + "oauth2/authorize"
_WEBHOOK_URL_ADD = _BASE_URL + "api/addwebhook"
_WEBHOOK_URL_DROP = _BASE_URL + "api/dropwebhook"


# Possible scops
ALL_SCOPES = [
    "read_station",
    "read_camera",
    "access_camera",
    "write_camera",
    "read_presence",
    "access_presence",
    "write_presence",
    "read_homecoach",
    "read_smokedetector",
    "read_thermostat",
    "write_thermostat",
]


class NetatmOAuth2:
    """
    Handle authentication with OAuth2

    :param client_id: Application client ID delivered by Netatmo on dev.netatmo.com
    :param client_secret: Application client secret delivered by Netatmo on dev.netatmo.com
    :param redirect_uri: Redirect URI where to the authorization server will redirect with an authorization code
    :param token: Authorization token
    :param token_updater: Callback when the token is updated
    :param scope:
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
    """

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        redirect_uri: Optional[str] = None,
        token: Optional[Dict[str, str]] = None,
        token_updater: Optional[Callable[[str], None]] = None,
        scope: Optional[str] = "read_station",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_updater = token_updater
        if token:
            self.scope = " ".join(token["scope"])
        else:
            self.scope = " ".join(ALL_SCOPES) if not scope else scope

        self.extra = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        self._oauth = OAuth2Session(
            client_id=self.client_id,
            token=token,
            token_updater=self.token_updater,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
        )

    def refresh_tokens(self) -> Dict[str, Union[str, int]]:
        """Refresh and return new tokens."""
        token = self._oauth.refresh_token(_AUTH_REQ, **self.extra)

        if self.token_updater is not None:
            self.token_updater(token)

        return token

    def post_request(
        self, url: str, params: Optional[Dict[str, str]] = None, timeout: int = 5
    ):
        """Wrapper for post requests."""
        if not params:
            params = {}

        if "json" in params:
            json_params = params.pop("json")
        else:
            json_params = None

        if "http://" in url:
            try:
                resp = requests.post(url, data=params, timeout=timeout)
            except requests.exceptions.ChunkedEncodingError:
                LOG.debug("Encoding error when connecting to '%s'", url)
            except requests.exceptions.ConnectTimeout:
                LOG.debug("Connection to %s timed out", url)
            except requests.exceptions.ConnectionError:
                LOG.debug("Remote end closed connection without response (%s)", url)
        else:

            def query(url, params, timeout, retries):
                if retries == 0:
                    LOG.error("Too many retries")
                    return
                try:
                    if json_params:
                        rsp = self._oauth.post(
                            url=url, json=json_params, timeout=timeout
                        )
                    else:
                        rsp = self._oauth.post(url=url, data=params, timeout=timeout)

                    return rsp
                except (
                    TokenExpiredError,
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectionError,
                ):
                    self._oauth.token = self.refresh_tokens()
                    # Sleep for 1 sec to prevent authentication related
                    # timeouts after a token refresh.
                    sleep(1)
                    return query(url, params, timeout, retries - 1)

            resp = query(url, params, timeout, 3)

        if resp is None:
            LOG.debug("Resp is None - %s", resp)
        elif not resp.ok:
            LOG.debug("The Netatmo API returned %s", resp.status_code)
            LOG.debug("Netato API error: %s", resp.content)
            try:
                raise ApiError(
                    f"{resp.status_code} - "
                    f"{ERRORS.get(resp.status_code, '')} - "
                    f"{resp.json()['error']['message']} "
                    f"({resp.json()['error']['code']}) "
                    f"when accessing '{url}'"
                )
            except JSONDecodeError:
                raise ApiError(
                    f"{resp.status_code} - "
                    f"{ERRORS.get(resp.status_code, '')} - "
                    f"when accessing '{url}'"
                )

        try:
            return (
                resp.json()
                if "application/json" in resp.headers.get("content-type")
                else resp.content
            )
        except (TypeError, AttributeError):
            LOG.debug("Invalid response %s", resp)
        return None

    def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        return self._oauth.authorization_url(_AUTH_URL, state)

    def request_token(
        self, authorization_response: Optional[str] = None, code: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generic method for fetching a Netatmo access token.
        :param authorization_response: Authorization response URL, the callback
                                       URL of the request back to you.
        :param code: Authorization code
        :return: A token dict
        """
        return self._oauth.fetch_token(
            _AUTH_REQ,
            authorization_response=authorization_response,
            code=code,
            client_secret=self.client_secret,
            include_client_id=True,
        )

    def addwebhook(self, webhook_url):
        postParams = {"url": webhook_url}
        resp = self.post_request(_WEBHOOK_URL_ADD, postParams)
        LOG.debug("addwebhook: %s", resp)

    def dropwebhook(self):
        postParams = {"app_types": "app_security"}
        resp = self.post_request(_WEBHOOK_URL_DROP, postParams)
        LOG.debug("dropwebhook: %s", resp)


class ClientAuth(NetatmOAuth2):
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
    """

    def __init__(
        self, clientId, clientSecret, username, password, scope="read_station"
    ):
        self._clientId = clientId
        self._clientSecret = clientSecret

        self._oauth = OAuth2Session(client=LegacyApplicationClient(client_id=clientId))
        self._oauth.fetch_token(
            token_url=_AUTH_REQ,
            username=username,
            password=password,
            client_id=clientId,
            client_secret=clientSecret,
            scope=scope,
        )
