from .helpers import BASE_URL
from .weather_station import WeatherStationData

_GETHOMECOACHDATA_REQ = BASE_URL + "api/gethomecoachsdata"


class HomeCoachData(WeatherStationData):
    """
    List the Home Couch devices (stations and modules)
    Args:
        auth_data (ClientAuth): Authentication information with a working access Token
    """

    def __init__(self, auth_data):
        super(HomeCoachData, self).__init__(auth_data, url_req=_GETHOMECOACHDATA_REQ)
