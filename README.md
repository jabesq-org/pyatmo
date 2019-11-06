netatmo-api-python
==================

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![GitHub Actions](https://github.com/jabesq/netatmo-api-python/workflows/Python%20package/badge.svg)](https://github.com/jabesq/netatmo-api-python/actions?workflow=Python+package)
[![PyPi](https://img.shields.io/pypi/v/pyatmo.svg)](https://pypi.python.org/pypi/pyatmo)
[![PyPi](https://img.shields.io/pypi/l/pyatmo.svg)](https://github.com/jabesq/netatmo-api-python/blob/master/LICENSE.txt)

Simple API to access Netatmo devices and data like weather station or camera data from Python 3.
For more detailed information see [dev.netatmo.com](http://dev.netatmo.com)

This project has no relation with the Netatmo company.

Install
-------

To install pyatmo simply run:

    pip install pyatmo

Depending on your permissions you might be required to use sudo.
Once installed you can simple add `pyatmo` to your Python 3 scripts by including:

    import pyatmo

Note
----

The module requires a valid user account and a registered application. See [usage.md](./usage.md) for further information.
Be aware that the module may stop working if Netatmo decides to change their API.

Development
-----------

To add the pre-commit hook to your environment run:

    pip install pre-commit flake8 mypy black isort
    pre-commit install

Testing
-------

To run the pytest testsuite you need to install the following dependencies:

    pip install pytest pytest-mock pytest-cov requests-mock freezegun

`pyatmo` has to be installed in editable mode to be picked up by pytest. Simply run:

    pip install -e .

To run the full suite simply type in

    pytest

or

    python -m pytest tests/

To generate code coverage xml (e.g. for use in VSCode) run

    python -m pytest --cov-report xml:cov.xml --cov smart_home --cov-append tests/

Another way to run the tests is by using `tox`. This runs the tests against the installed package and multiple versions of python.

    tox

or by specifying a python version

    tox -e py38
