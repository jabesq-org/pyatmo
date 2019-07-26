# Published Jan 2013
# Revised Jan 2014 (to add new modules data)
# Author : Philippe Larduinat, philippelt@users.sourceforge.net
# Public domain source code
"""
This API provides access to the Netatmo weather station or/and the Netatmo
cameras or/and the Netatmo smart thermostat
This package can be used with Python3 applications
PythonAPI Netatmo REST data access
"""
import logging
import time

from smart_home import _BASE_URL, postRequest
from smart_home.Camera import CameraData
from smart_home.HomeCoach import HomeCoachData
from smart_home.PublicData import PublicData
from smart_home.Thermostat import HomeData, HomeStatus
from smart_home.WeatherStation import WeatherStationData
from smart_home.Exceptions import NoDevice, InvalidHome, InvalidRoom, NoSchedule

LOG = logging.getLogger(__name__)


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
        scope (Optional[str]): Default value is 'read_station'
            read_station: to retrieve weather station data (Getstationsdata, Getmeasure)
            read_camera: to retrieve Welcome data (Gethomedata, Getcamerapicture)
            access_camera: to access the camera, the videos and the live stream.
            read_thermostat: to retrieve thermostat data (Getmeasure, Getthermostatsdata)
            write_thermostat: to set up the thermostat (Syncschedule, Setthermpoint)
            read_presence: to retrieve Presence data (Gethomedata, Getcamerapicture)
            read_homecoach: to retrieve Home Coache data (Gethomecoachsdata)
            access_presence: to access the live stream, any video stored on the SD card and to retrieve Presence's lightflood status
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
        except (KeyError):
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


# auto-test when executed directly

if __name__ == "__main__":

    from sys import exit, stdout, stderr

    try:
        import os

        if (
            os.environ["CLIENT_ID"]
            and os.environ["CLIENT_SECRET"]
            and os.environ["USERNAME"]
            and os.environ["PASSWORD"]
        ):
            CLIENT_ID = os.environ["CLIENT_ID"]
            CLIENT_SECRET = os.environ["CLIENT_SECRET"]
            USERNAME = os.environ["USERNAME"]
            PASSWORD = os.environ["PASSWORD"]
    except KeyError:
        stderr.write(
            "No credentials passed to pyatmo.py (client_id, client_secret, username, password)\n"
        )
        exit(1)

    authorization = ClientAuth(
        clientId=CLIENT_ID,
        clientSecret=CLIENT_SECRET,
        username=USERNAME,
        password=PASSWORD,
        scope="read_station read_camera access_camera read_thermostat write_thermostat read_presence access_presence",
    )

    try:
        ws = WeatherStationData(authorization)
    except NoDevice:
        if stdout.isatty():
            print("pyatmo.py : warning, no weather station available for testing")

    try:
        cam = CameraData(authorization)
    except NoDevice:
        if stdout.isatty():
            print("pyatmo.py : warning, no camera available for testing")

    try:
        hd = HomeData(authorization)
    except NoDevice:
        if stdout.isatty():
            print("pyatmo.py : warning, no thermostat available for testing")

    PublicData(authorization)

    # If we reach this line, all is OK

    # If launched interactively, display OK message
    if stdout.isatty():
        print("pyatmo.py : OK")

    exit(0)
