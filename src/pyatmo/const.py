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
    "access_camera",
    "access_presence",
    "read_bubendorff",  # Bubbendorf shutters
    "read_camera",
    "read_doorbell",  # Smart Video Doorbell
    "read_homecoach",  # Smart Indoor Air Quality Monitor
    "read_magellan",  # Legrand Wiring device or Electrical panel products
    "read_mx",  # BTicino Classe 300 EOS
    "read_presence",
    "read_smarther",  # Smarther with Netatmo thermostat
    "read_smokedetector",  # Smart Smoke Alarm informations and events
    "read_station",
    "read_thermostat",
    "write_camera",
    "write_presence",
    "write_thermostat",
]

MANUAL = "manual"
HOME = "home"
FROSTGUARD = "hg"


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
