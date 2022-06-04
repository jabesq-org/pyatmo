"""Common constants."""
from __future__ import annotations

from typing import Any, Dict

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

# Special types
RawData = Dict[str, Any]

DEFAULT_BASE_URL: str = "https://api.netatmo.com/"

# Endpoints
AUTH_REQ_ENDPOINT = "oauth2/token"
AUTH_URL_ENDPOINT = "oauth2/authorize"
WEBHOOK_URL_ADD_ENDPOINT = "api/addwebhook"
WEBHOOK_URL_DROP_ENDPOINT = "api/dropwebhook"

GETHOMESDATA_ENDPOINT = "api/homesdata"
GETHOMESTATUS_ENDPOINT = "api/homestatus"
GETEVENTS_ENDPOINT = "api/getevents"
SETTHERMMODE_ENDPOINT = "api/setthermmode"
SETROOMTHERMPOINT_ENDPOINT = "api/setroomthermpoint"
GETROOMMEASURE_ENDPOINT = "api/getroommeasure"
SWITCHHOMESCHEDULE_ENDPOINT = "api/switchhomeschedule"

GETHOMEDATA_ENDPOINT = "api/gethomedata"
GETCAMERAPICTURE_ENDPOINT = "api/getcamerapicture"
GETEVENTSUNTIL_ENDPOINT = "api/geteventsuntil"
SETPERSONSAWAY_ENDPOINT = "api/setpersonsaway"
SETPERSONSHOME_ENDPOINT = "api/setpersonshome"
SETSTATE_ENDPOINT = "api/setstate"

GETHOMECOACHDATA_ENDPOINT = "api/gethomecoachsdata"

GETMEASURE_ENDPOINT = "api/getmeasure"
GETSTATIONDATA_ENDPOINT = "api/getstationsdata"

GETPUBLIC_DATA_ENDPOINT = "api/getpublicdata"

AUTHORIZATION_HEADER = "Authorization"

# Possible scops
ALL_SCOPES = [
    "access_camera",  # Netatmo camera products
    "access_doorbell",  # Netatmo Smart Video Doorbell
    "access_presence",  # Netatmo Smart Outdoor Camera
    "read_bubendorff",  # Bubbendorf shutters
    "read_camera",  # Netatmo camera products
    "read_carbonmonoxidedetector",  # Netatmo CO sensor
    "read_doorbell",  # Netatmo Smart Video Doorbell
    "read_homecoach",  # Netatmo Smart Indoor Air Quality Monitor
    "read_magellan",  # Legrand Wiring device or Electrical panel products
    "read_mx",  # BTicino Classe 300 EOS
    "read_presence",  # Netatmo Smart Outdoor Camera
    "read_smarther",  # Smarther with Netatmo thermostat
    "read_smokedetector",  # Smart Smoke Alarm information and events
    "read_station",  # Netatmo weather station
    "read_thermostat",  # Netatmo climate products
    "write_bubendorff",  # Bubbendorf shutters
    "write_camera",  # Netatmo camera products
    "write_magellan",  # Legrand Wiring device or Electrical panel products
    "write_mx",  # BTicino Classe 300 EOS
    "write_presence",  # Netatmo Smart Outdoor Camera
    "write_smarther",  # Smarther products
    "write_thermostat",  # Netatmo climate products
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
