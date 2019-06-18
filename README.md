netatmo-api-python
==================
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Simple API to access Netatmo devices and data like weather station or camera data from Python 3.
For more detailed information see http://dev.netatmo.com

This project has no relation with the Netatmo company.

### Install ###

To install pyatmo simply run:

    pip install pyatmo

Depending on your permissions you might be required to use sudo.
Once installed you can simple add `pyatmo` to your Python 3 scripts by including:

    import pyatmo

### Note ###

The module requires a valid user account and a registered application. See usage.md for further information.
Be aware that the module may stop working if Netatmo decides to change their API.


### Testing ###

To run the pytest testsuite you need to install the following dependencies:

    pip install pytest pytest-mock pytest-cov requests-mock freezegun

To run the full suite simply type in

    pytest

or

    python -m pytest

To generate code coverage xml (e.g. for use in VSCode) run

    python -m pytest --cov-report xml:cov.xml --cov smart_home --cov-append tests/