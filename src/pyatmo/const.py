"""Common constants."""

from __future__ import annotations

ERRORS: dict[int, str] = {
    400: "Bad request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not found",
    406: "Not Acceptable",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}

_BASE_URL: str = "https://api.netatmo.com/"

# Endpoints
AUTH_REQ_ENDPOINT = "oauth2/token"
AUTH_REQ = _BASE_URL + AUTH_REQ_ENDPOINT
AUTH_URL_ENDPOINT = "oauth2/authorize"
AUTH_URL = _BASE_URL + AUTH_URL_ENDPOINT
WEBHOOK_URL_ADD = f'{_BASE_URL}api/addwebhook'
WEBHOOK_URL_DROP = f'{_BASE_URL}api/dropwebhook'

_GETHOMESDATA_REQ = f'{_BASE_URL}api/homesdata'
_GETHOMESTATUS_REQ = f'{_BASE_URL}api/homestatus'
_SETTHERMMODE_REQ = f'{_BASE_URL}api/setthermmode'
_SETROOMTHERMPOINT_REQ = f'{_BASE_URL}api/setroomthermpoint'
_GETROOMMEASURE_REQ = f'{_BASE_URL}api/getroommeasure'
_SWITCHHOMESCHEDULE_REQ = f'{_BASE_URL}api/switchhomeschedule'

_GETHOMEDATA_REQ = f'{_BASE_URL}api/gethomedata'
_GETCAMERAPICTURE_REQ = f'{_BASE_URL}api/getcamerapicture'
_GETEVENTSUNTIL_REQ = f'{_BASE_URL}api/geteventsuntil'
_SETPERSONSAWAY_REQ = f'{_BASE_URL}api/setpersonsaway'
_SETPERSONSHOME_REQ = f'{_BASE_URL}api/setpersonshome'
_SETSTATE_REQ = f'{_BASE_URL}api/setstate'

_GETHOMECOACHDATA_REQ = f'{_BASE_URL}api/gethomecoachsdata'

_GETMEASURE_REQ = f'{_BASE_URL}api/getmeasure'
_GETSTATIONDATA_REQ = f'{_BASE_URL}api/getstationsdata'

_GETPUBLIC_DATA = f'{_BASE_URL}api/getpublicdata'

AUTHORIZATION_HEADER = "Authorization"

# Possible scops
ALL_SCOPES = [
    "read_station",
    "read_camera",
    "access_camera",
    "write_camera",
    "read_presence",
    "access_presence",
    "write_presence",
    "read_homecoach",  # Smart Indoor Air Quality Monitor
    "read_smokedetector",  # Smart Smoke Alarm informations and events
    "read_thermostat",
    "write_thermostat",
    "read_magellan",  # Legrand Wiring device or Electrical panel products
    "read_bubendorff",  # Bubbendorf shutters
    "read_smarther",  # Smarther with Netatmo thermostat
    "read_doorbell",  # Smart Video Doorbell
    "read_mx",  # BTicino Classe 300 EOS
]

MANUAL = "manual"
HOME = "home"
FROSTGUARD = "hg"
