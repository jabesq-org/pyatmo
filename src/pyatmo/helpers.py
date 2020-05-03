import logging
import time
from calendar import timegm
from datetime import datetime

LOG = logging.getLogger(__name__)

_BASE_URL = "https://api.netatmo.com/"

ERRORS = {
    400: "Bad request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not found",
    406: "Not Acceptable",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def toTimeString(value):
    return datetime.utcfromtimestamp(int(value)).isoformat(sep="_")


def toEpoch(value):
    return timegm(time.strptime(value + "GMT", "%Y-%m-%d_%H:%M:%S%Z"))


def todayStamps():
    today = timegm(time.strptime(time.strftime("%Y-%m-%d") + "GMT", "%Y-%m-%d%Z"))
    return today, today + 3600 * 24


def fixId(rawData):
    if rawData:
        for station in rawData:
            station["_id"] = station["_id"].replace(" ", "")
            for module in station.get("modules", {}):
                module["_id"] = module["_id"].replace(" ", "")
    return rawData
