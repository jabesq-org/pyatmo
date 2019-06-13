"""Define tests for WeatherStation module."""
import json

import pytest

import smart_home.WeatherStation

from contextlib import contextmanager


@contextmanager
def does_not_raise():
    yield


def test_WeatherStationData(weatherStationData):
    assert weatherStationData.default_station == "MyStation"
