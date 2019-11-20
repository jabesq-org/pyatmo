import time

from .exceptions import NoDevice
from .helpers import _BASE_URL, LOG, postRequest

# Common definitions
_AUTH_REQ = _BASE_URL + "oauth2/token"
_WEBHOOK_URL_ADD = _BASE_URL + "api/addwebhook"
_WEBHOOK_URL_DROP = _BASE_URL + "api/dropwebhook"


class ClientAuth:
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
            access_camera: to access the camera, the videos and the live stream.
            write_camera: to set home/away status of persons (Setpersonsaway, Setpersonshome)
            read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
            write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
            read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
            access_presence: to access the live stream, any video stored on the SD card and to retrieve Presence's lightflood status
            read_homecoach: to retrieve Home Coache data (Gethomecoachsdata)
            read_smokedetector: to read the smoke detector status (Gethomedata)
            Several value can be used at the same time, ie: 'read_station read_camera'
    """

    def __init__(
        self, clientId, clientSecret, username, password, scope="read_station"
    ):
        postParams = {
            "grant_type": "password",
            "client_id": clientId,
            "client_secret": clientSecret,
            "username": username,
            "password": password,
            "scope": scope,
        }
        resp = postRequest(_AUTH_REQ, postParams)
        self._clientId = clientId
        self._clientSecret = clientSecret
        try:
            self._accessToken = resp["access_token"]
        except KeyError:
            LOG.error("Netatmo API returned %s", resp["error"])
            raise NoDevice("Authentication against Netatmo API failed")
        self.refreshToken = resp["refresh_token"]
        self._scope = resp["scope"]
        self.expiration = int(resp["expire_in"] + time.time() - 1800)

    def addwebhook(self, webhook_url):
        postParams = {
            "access_token": self._accessToken,
            "url": webhook_url,
            "app_types": "app_security",
        }
        resp = postRequest(_WEBHOOK_URL_ADD, postParams)
        LOG.debug("addwebhook: %s", resp)

    def dropwebhook(self):
        postParams = {"access_token": self._accessToken, "app_types": "app_security"}
        resp = postRequest(_WEBHOOK_URL_DROP, postParams)
        LOG.debug("dropwebhook: %s", resp)

    @property
    def accessToken(self):

        if self.expiration < time.time():  # Token should be renewed
            postParams = {
                "grant_type": "refresh_token",
                "refresh_token": self.refreshToken,
                "client_id": self._clientId,
                "client_secret": self._clientSecret,
            }
            resp = postRequest(_AUTH_REQ, postParams)
            self._accessToken = resp["access_token"]
            self.refreshToken = resp["refresh_token"]
            self.expiration = int(resp["expire_in"] + time.time() - 1800)
        return self._accessToken
