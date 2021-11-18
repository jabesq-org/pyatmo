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

_DEFAULT_BASE_URL: str = "https://api.netatmo.com/"

# Endpoints
AUTH_REQ_ENDPOINT = "oauth2/token"
AUTH_URL_ENDPOINT = "oauth2/authorize"
WEBHOOK_URL_ADD_ENDPOINT = "api/addwebhook"
WEBHOOK_URL_DROP_ENDPOINT = "api/dropwebhook"

_GETHOMESDATA_ENDPOINT = "api/homesdata"
_GETHOMESTATUS_ENDPOINT = "api/homestatus"
_SETTHERMMODE_ENDPOINT = "api/setthermmode"
_SETROOMTHERMPOINT_ENDPOINT = "api/setroomthermpoint"
_GETROOMMEASURE_ENDPOINT = "api/getroommeasure"
_SWITCHHOMESCHEDULE_ENDPOINT = "api/switchhomeschedule"

_GETHOMEDATA_ENDPOINT = "api/gethomedata"
_GETCAMERAPICTURE_ENDPOINT = "api/getcamerapicture"
_GETEVENTSUNTIL_ENDPOINT = "api/geteventsuntil"
_SETPERSONSAWAY_ENDPOINT = "api/setpersonsaway"
_SETPERSONSHOME_ENDPOINT = "api/setpersonshome"
_SETSTATE_ENDPOINT = "api/setstate"

_GETHOMECOACHDATA_ENDPOINT = "api/gethomecoachsdata"

_GETMEASURE_ENDPOINT = "api/getmeasure"
_GETSTATIONDATA_ENDPOINT = "api/getstationsdata"

_GETPUBLIC_DATA_ENDPOINT = "api/getpublicdata"

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
