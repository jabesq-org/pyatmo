import logging
import time
from calendar import timegm
from datetime import datetime

import requests

LOG = logging.getLogger(__name__)

# Common definitions
_BASE_URL = "https://api.netatmo.com/"


# Utilities routines


def postRequest(url, params=None, timeout=10):
    resp = requests.post(url, data=params, timeout=timeout)
    if not resp.ok:
        LOG.error("The Netatmo API returned %s", resp.status_code)
    try:
        return (
            resp.json()
            if "application/json" in resp.headers.get("content-type")
            else resp.content
        )
    except TypeError:
        LOG.debug("Invalid response %s", resp)
    return None


def toTimeString(value):
    return datetime.utcfromtimestamp(int(value)).isoformat(sep="_")


def toEpoch(value):
    return timegm(time.strptime(value + "GMT", "%Y-%m-%d_%H:%M:%S%Z"))


def todayStamps():
    today = timegm(time.strptime(time.strftime("%Y-%m-%d") + "GMT", "%Y-%m-%d%Z"))
    return today, today + 3600 * 24


# Global shortcut


def getStationMinMaxTH(station=None, module=None):
    from pyatmo import ClientAuth
    from smart_home.WeatherStation import DeviceList

    authorization = ClientAuth()
    devList = DeviceList(authorization)
    if not station:
        station = devList.default_station
    if module:
        mname = module
    else:
        mname = devList.stationByName(station)["module_name"]
    lastD = devList.lastData(station)
    if mname == "*":
        result = {}
        for m in lastD.keys():
            if time.time() - lastD[m]["When"] > 3600:
                continue
            r = devList.MinMaxTH(module=m)
            result[m] = (r[0], lastD[m]["Temperature"], r[1])
    else:
        if time.time() - lastD[mname]["When"] > 3600:
            result = ["-", "-"]
        else:
            result = [lastD[mname]["Temperature"], lastD[mname]["Humidity"]]
        result.extend(devList.MinMaxTH(station, mname))
    return result
