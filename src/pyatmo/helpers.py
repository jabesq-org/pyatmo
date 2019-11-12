import logging
import time
from calendar import timegm
from datetime import datetime

import requests

LOG = logging.getLogger(__name__)

_BASE_URL = "https://api.netatmo.com/"


def postRequest(url, params=None, timeout=30):
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
