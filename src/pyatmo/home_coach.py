from .auth import NetatmoOAuth2
from .helpers import _BASE_URL
from .weather_station import WeatherStationData

_GETHOMECOACHDATA_REQ = _BASE_URL + "api/gethomecoachsdata"


class HomeCoachData(WeatherStationData):
    """
    Class of Netatmo Home Couch devices (stations and modules)
    """

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token

        Raises:
            NoDevice: No devices found.
        """
        super().__init__(auth, url_req=_GETHOMECOACHDATA_REQ)
