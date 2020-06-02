from .auth import NetatmOAuth2
from .helpers import _BASE_URL
from .weather_station import WeatherStationData

_GETHOMECOACHDATA_REQ = BASE_URL + "api/gethomecoachsdata"


class HomeCoachData(WeatherStationData):
    """
    Class of Netatmo Home Couch devices (stations and modules)
    """

    def __init__(self, auth: NetatmOAuth2) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmOAuth2} -- Authentication information with a valid access token

        Raises:
            NoDevice: No devices found.
        """
        super(HomeCoachData, self).__init__(auth, url_req=_GETHOMECOACHDATA_REQ)
