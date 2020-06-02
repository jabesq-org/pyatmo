import logging
import time
from calendar import timegm
from datetime import datetime
from typing import Dict, Tuple

LOG: logging.Logger = logging.getLogger(__name__)

_BASE_URL: str = "https://api.netatmo.com/"

ERRORS: Dict[int, str] = {
    400: "Bad request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not found",
    406: "Not Acceptable",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def to_time_string(value: str) -> str:
    return datetime.utcfromtimestamp(int(value)).isoformat(sep="_")


def to_epoch(value: str) -> int:
    return timegm(time.strptime(value + "GMT", "%Y-%m-%d_%H:%M:%S%Z"))


def today_stamps() -> Tuple[int, int]:
    today: int = timegm(time.strptime(time.strftime("%Y-%m-%d") + "GMT", "%Y-%m-%d%Z"))
    return today, today + 3600 * 24


def fix_id(raw_data: Dict) -> Dict:
    if raw_data:
        for station in raw_data:
            station["_id"] = station["_id"].replace(" ", "")
            for module in station.get("modules", {}):
                module["_id"] = module["_id"].replace(" ", "")
    return raw_data
