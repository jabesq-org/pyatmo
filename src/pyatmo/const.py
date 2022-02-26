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
WEBHOOK_URL_ADD = _BASE_URL + "api/addwebhook"
WEBHOOK_URL_DROP = _BASE_URL + "api/dropwebhook"

_GETHOMESDATA_REQ = _BASE_URL + "api/homesdata"
_GETHOMESTATUS_REQ = _BASE_URL + "api/homestatus"
_GETEVENTS_REQ = _BASE_URL + "api/getevents"
_SETTHERMMODE_REQ = _BASE_URL + "api/setthermmode"
_SETROOMTHERMPOINT_REQ = _BASE_URL + "api/setroomthermpoint"
_GETROOMMEASURE_REQ = _BASE_URL + "api/getroommeasure"
_SWITCHHOMESCHEDULE_REQ = _BASE_URL + "api/switchhomeschedule"

_GETHOMEDATA_REQ = _BASE_URL + "api/gethomedata"
_GETCAMERAPICTURE_REQ = _BASE_URL + "api/getcamerapicture"
_GETEVENTSUNTIL_REQ = _BASE_URL + "api/geteventsuntil"
_SETPERSONSAWAY_REQ = _BASE_URL + "api/setpersonsaway"
_SETPERSONSHOME_REQ = _BASE_URL + "api/setpersonshome"
_SETSTATE_REQ = _BASE_URL + "api/setstate"

_GETHOMECOACHDATA_REQ = _BASE_URL + "api/gethomecoachsdata"

_GETMEASURE_REQ = _BASE_URL + "api/getmeasure"
_GETSTATIONDATA_REQ = _BASE_URL + "api/getstationsdata"

_GETPUBLIC_DATA = _BASE_URL + "api/getpublicdata"

AUTHORIZATION_HEADER = "Authorization"

# Possible scops
ALL_SCOPES = [
    "access_camera",
    "access_doorbell",  # Smart Video Doorbell
    "access_presence",
    "read_bubendorff",  # Bubbendorf shutters
    "read_camera",
    "read_carbonmonoxidedetector",
    "read_doorbell",  # Smart Video Doorbell
    "read_homecoach",  # Smart Indoor Air Quality Monitor
    "read_magellan",  # Legrand Wiring device or Electrical panel products
    "read_mx",  # BTicino Classe 300 EOS
    "read_presence",
    "read_smarther",  # Smarther with Netatmo thermostat
    "read_smokedetector",  # Smart Smoke Alarm informations and events
    "read_station",
    "read_thermostat",
    "write_bubendorff",  # Bubbendorf shutters
    "write_camera",
    "write_magellan",
    "write_mx",  # BTicino Classe 300 EOS
    "write_presence",
    "write_smarther",
    "write_thermostat",
]

MANUAL = "manual"
HOME = "home"
FROSTGUARD = "hg"
SCHEDULES = "schedules"
EVENTS = "events"


STATION_TEMPERATURE_TYPE = "temperature"
STATION_PRESSURE_TYPE = "pressure"
STATION_HUMIDITY_TYPE = "humidity"

ACCESSORY_RAIN_LIVE_TYPE = "rain_live"
ACCESSORY_RAIN_60MIN_TYPE = "rain_60min"
ACCESSORY_RAIN_24H_TYPE = "rain_24h"
ACCESSORY_RAIN_TIME_TYPE = "rain_timeutc"
ACCESSORY_WIND_STRENGTH_TYPE = "wind_strength"
ACCESSORY_WIND_ANGLE_TYPE = "wind_angle"
ACCESSORY_WIND_TIME_TYPE = "wind_timeutc"
ACCESSORY_GUST_STRENGTH_TYPE = "gust_strength"
ACCESSORY_GUST_ANGLE_TYPE = "gust_angle"
