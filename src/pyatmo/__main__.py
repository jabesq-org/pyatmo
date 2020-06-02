from pyatmo.auth import ALL_SCOPES, ClientAuth
from pyatmo.camera import CameraData
from pyatmo.exceptions import NoDevice
from pyatmo.public_data import PublicData
from pyatmo.thermostat import HomeData
from pyatmo.weather_station import WeatherStationData


def main():
    import sys

    try:
        import os

        if (
            os.environ["CLIENT_ID"]
            and os.environ["CLIENT_SECRET"]
            and os.environ["USERNAME"]
            and os.environ["PASSWORD"]
        ):
            CLIENT_ID = os.environ["CLIENT_ID"]
            CLIENT_SECRET = os.environ["CLIENT_SECRET"]
            USERNAME = os.environ["USERNAME"]
            PASSWORD = os.environ["PASSWORD"]
    except KeyError:
        sys.stderr.write(
            "No credentials passed to pyatmo.py (client_id, client_secret, username, password)\n"
        )
        sys.exit(1)

    auth = ClientAuth(
        clientId=CLIENT_ID,
        clientSecret=CLIENT_SECRET,
        username=USERNAME,
        password=PASSWORD,
        scope=" ".join(ALL_SCOPES),
    )

    try:
        WeatherStationData(auth)
    except NoDevice:
        if sys.stdout.isatty():
            print("pyatmo.py : warning, no weather station available for testing")

    try:
        CameraData(auth)
    except NoDevice:
        if sys.stdout.isatty():
            print("pyatmo.py : warning, no camera available for testing")

    try:
        HomeData(auth)
    except NoDevice:
        if sys.stdout.isatty():
            print("pyatmo.py : warning, no thermostat available for testing")

    PublicData(auth)

    # If we reach this line, all is OK

    # If launched interactively, display OK message
    if sys.stdout.isatty():
        print("pyatmo: OK")

    sys.exit(0)


if __name__ == "__main__":
    main()
