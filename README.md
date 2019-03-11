netatmo-api-python
==================
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Simple API to access Netatmo devices and data like weather station or camera data from python.
For more detailed information see http://dev.netatmo.com

This project has no relation with the Netatmo company.

### Install ###

To install pyatmo simply run:

    pip install pyatmo

Depending on your permissions you might be required to use sudo.
Once installed you can simple add `pyatmo` to your python scripts by including:

    import pyatmo

### Note ###

The module requires a valid user account and a registered application. See usage.md for further information.
Be aware that the module may stop working if Netatmo decides to change their API.
