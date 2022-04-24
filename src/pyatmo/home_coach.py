from .auth import AbstractAsyncAuth, NetatmoOAuth2
from .weather_station import AsyncWeatherStationData, WeatherStationData

_GETHOMECOACHDATA_ENDPOINT = "api/gethomecoachsdata"


class HomeCoachData(WeatherStationData):
    """
    Class of Netatmo Home Coach devices (stations and modules)
    """

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with a valid access token
        """
        super().__init__(auth, endpoint=_GETHOMECOACHDATA_ENDPOINT, favorites=False)


class AsyncHomeCoachData(AsyncWeatherStationData):
    """
    Class of Netatmo Home Coach devices (stations and modules)
    """

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize self.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with a valid access token
        """
        super().__init__(auth, endpoint=_GETHOMECOACHDATA_ENDPOINT, favorites=False)
