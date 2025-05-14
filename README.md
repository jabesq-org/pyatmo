# pyatmo

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![GitHub Actions](https://github.com/jabesq/pyatmo/workflows/Python%20package/badge.svg)](https://github.com/jabesq/pyatmo/actions?workflow=Python+package)
[![PyPi](https://img.shields.io/pypi/v/pyatmo.svg)](https://pypi.python.org/pypi/pyatmo)
[![license](https://img.shields.io/pypi/l/pyatmo.svg)](https://github.com/jabesq/pyatmo/blob/master/LICENSE.txt)

> **Warning:**
> Due to personal reasons, I am currently unable to dedicate sufficient time to effectively manage this repository. Consequently, no attention will be given to existing or forthcoming issues until further notice. **However**, I want to assure you that I will continue to merge any pull requests that are submitted, provided they successfully pass the continuous integration tests and do not exhibit any glaring issues.
>
> I apologize for any inconvenience this may cause, and I sincerely hope to have the capacity to allocate more time to this repository in the near future. Your understanding is greatly appreciated.
>
> *Hugo DUPRAS (jabesq)*

---

Simple API to access Netatmo devices and data like weather station or camera data from Python 3.
For more detailed information see [dev.netatmo.com](http://dev.netatmo.com)

This project has no relation with the Netatmo company.

## Install

To install pyatmo simply run:

    pip install pyatmo

Depending on your permissions you might be required to use sudo.
Once installed you can simply add `pyatmo` to your Python 3 scripts by including:

    import pyatmo

## Note

The module requires a valid user account and a registered application.
Be aware that the module may stop working if Netatmo decides to change their API.

## Development

Prerequisits:

    uv
    python >=3.11

Clone the repo, install dependencies and install pre-commit hooks:

    git clone
    cd pyatmo
    uv sync
    pre-commit install

## Testing

To run the full suite simply run the following command from within the virtual environment:

    pytest

or

    python -m pytest tests/

To generate code coverage xml (e.g. for use in VSCode) run

    python -m pytest --cov-report xml:cov.xml --cov pyatmo --cov-append tests/

Another way to run the tests is by using `tox`. This runs the tests against the installed package and multiple versions of python.

    tox

or by specifying a python version

    tox -e py310
