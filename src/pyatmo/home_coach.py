"""Support for Netatmo air care devices."""
from warnings import warn

from pyatmo.auth import AbstractAsyncAuth, NetatmoOAuth2
from pyatmo.const import GETHOMECOACHDATA_ENDPOINT
from pyatmo.weather_station import AsyncWeatherStationData, WeatherStationData

warn(f"The module {__name__} is deprecated.", DeprecationWarning, stacklevel=2)


class HomeCoachData(WeatherStationData):
    """
    Class of Netatmo Home Coach devices (stations and modules)
    """

    def __init__(self, auth: NetatmoOAuth2) -> None:
        """Initialize self.

        Arguments:
            auth {NetatmoOAuth2} -- Authentication information with valid access token
        """
        super().__init__(auth, endpoint=GETHOMECOACHDATA_ENDPOINT, favorites=False)


class AsyncHomeCoachData(AsyncWeatherStationData):
    """
    Class of Netatmo Home Coach devices (stations and modules)
    """

    def __init__(self, auth: AbstractAsyncAuth) -> None:
        """Initialize self.

        Arguments:
            auth {AbstractAsyncAuth} -- Authentication information with valid access token
        """
        super().__init__(auth, endpoint=GETHOMECOACHDATA_ENDPOINT, favorites=False)
