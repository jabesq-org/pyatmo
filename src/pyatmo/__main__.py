import os
import sys
from warnings import warn

from pyatmo.auth import ClientAuth
from pyatmo.camera import CameraData
from pyatmo.const import ALL_SCOPES
from pyatmo.exceptions import NoDevice
from pyatmo.home_coach import HomeCoachData
from pyatmo.public_data import PublicData
from pyatmo.thermostat import HomeData
from pyatmo.weather_station import WeatherStationData

LON_NE = "6.221652"
LAT_NE = "46.610870"
LON_SW = "6.217828"
LAT_SW = "46.596485"

warn(f"The module {__name__} is deprecated.", DeprecationWarning, stacklevel=2)


def tty_print(message: str) -> None:
    """Print to stdout if in an interactive terminal."""
    if sys.stdout.isatty():
        print(message)


def main() -> None:
    """Run basic health checks."""
    client_id = os.getenv("CLIENT_ID", "")
    client_secret = os.getenv("CLIENT_SECRET", "")
    username = os.getenv("USERNAME", "")
    password = os.getenv("PASSWORD", "")

    if not (client_id and client_secret and username and password):
        sys.stderr.write(
            "Missing credentials (client_id, client_secret, username, password)\n",
        )
        sys.exit(1)

    auth = ClientAuth(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        scope=" ".join(ALL_SCOPES),
    )

    try:
        ws_data = WeatherStationData(auth)
        ws_data.update()
    except NoDevice:
        tty_print("pyatmo: no weather station available for testing")

    try:
        hc_data = HomeCoachData(auth)
        hc_data.update()
    except NoDevice:
        tty_print("pyatmo: no home coach station available for testing")

    try:
        camera_data = CameraData(auth)
        camera_data.update()
    except NoDevice:
        tty_print("pyatmo: no camera available for testing")

    try:
        home_data = HomeData(auth)
        home_data.update()
    except NoDevice:
        tty_print("pyatmo: no thermostat available for testing")

    public_data = PublicData(auth, LAT_NE, LON_NE, LAT_SW, LON_SW)
    public_data.update()

    # If we reach this line, all is OK
    tty_print("pyatmo: OK")

    sys.exit(0)


if __name__ == "__main__":
    main()
