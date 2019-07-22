"""Define tests for WeatherStation module."""
import json

import pytest

from freezegun import freeze_time

from .conftest import does_not_raise

import smart_home.WeatherStation


def test_WeatherStationData(weatherStationData):
    assert weatherStationData.default_station == "MyStation"


def test_WeatherStationData_no_response(auth, requests_mock):
    requests_mock.post(smart_home.WeatherStation._GETSTATIONDATA_REQ, text="None")
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.WeatherStation.WeatherStationData(auth)


def test_WeatherStationData_no_body(auth, requests_mock):
    with open("fixtures/status_ok.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.WeatherStation._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.WeatherStation.WeatherStationData(auth)


def test_WeatherStationData_no_data(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.WeatherStation._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.WeatherStation.NoDevice):
        assert smart_home.WeatherStation.WeatherStationData(auth)


@pytest.mark.parametrize(
    "station, expected",
    [
        (
            None,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        (
            "MyStation",
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet."
            ),
        ),
    ],
)
def test_WeatherStationData_modulesNamesList(weatherStationData, station, expected):
    assert sorted(weatherStationData.modulesNamesList(station)) == expected


def test_WeatherStationData_stationByName(weatherStationData):
    result = weatherStationData.stationByName()
    assert result["_id"] == "12:34:56:37:11:ca"
    assert result["station_name"] == "MyStation"
    assert result["module_name"] == "NetatmoIndoor"
    assert result["type"] == "NAMain"
    assert result["data_type"] == [
        "Temperature",
        "CO2",
        "Humidity",
        "Noise",
        "Pressure",
    ]
    assert weatherStationData.stationByName("NoValidStation") is None


@pytest.mark.parametrize(
    "module, station, expected",
    [
        ("Kitchen", None, "12:34:56:07:bb:3e"),
        ("Kitchen", "MyStation", "12:34:56:07:bb:3e"),
        ("Kitchen", "NoValidStation", None),
        ("NetatmoIndoor", None, "12:34:56:37:11:ca"),
        ("NetatmoIndoor", "MyStation", "12:34:56:37:11:ca"),
        ("", None, None),
        ("", "", None),
        (None, None, None),
    ],
)
def test_WeatherStationData_moduleByName(weatherStationData, module, station, expected):
    mod = weatherStationData.moduleByName(module, station)
    if mod:
        assert mod["_id"] == expected
    else:
        assert mod is expected


@pytest.mark.parametrize(
    "mid, sid, expected",
    [
        ("12:34:56:07:bb:3e", None, "12:34:56:07:bb:3e"),
        ("12:34:56:07:bb:3e", "12:34:56:37:11:ca", "12:34:56:07:bb:3e"),
        ("", None, None),
        ("", "", None),
        (None, None, None),
    ],
)
def test_WeatherStationData_moduleById(weatherStationData, mid, sid, expected):
    mod = weatherStationData.moduleById(mid, sid)
    if mod:
        assert mod["_id"] == expected
    else:
        assert mod is expected


@pytest.mark.parametrize(
    "module, expected",
    [
        (
            "Kitchen",
            [
                "battery_percent",
                "battery_vp",
                "co2",
                "humidity",
                "max_temp",
                "min_temp",
                "rf_status",
                "temperature",
            ],
        ),
        (
            "Garden",
            [
                "battery_percent",
                "battery_vp",
                "gustangle",
                "guststrength",
                "rf_status",
                "windangle",
                "windstrength",
            ],
        ),
        (
            "Yard",
            [
                "Rain",
                "battery_percent",
                "battery_vp",
                "rf_status",
                "sum_rain_1",
                "sum_rain_24",
            ],
        ),
        (
            "NetatmoIndoor",
            [
                "co2",
                "humidity",
                "max_temp",
                "min_temp",
                "noise",
                "pressure",
                "temperature",
                "wifi_status",
            ],
        ),
        pytest.param(
            "12:34:56:07:bb:3e",
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
        pytest.param(
            "",
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
        pytest.param(
            None,
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
    ],
)
def test_WeatherStationData_monitoredConditions(weatherStationData, module, expected):
    assert sorted(weatherStationData.monitoredConditions(module)) == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, exclude, expected",
    [
        (
            "MyStation",
            None,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        (
            "",
            None,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        ("NoValidStation", None, None),
        (
            None,
            1000000,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        (
            None,
            798103,
            ["Garden", "Kitchen", "NetatmoIndoor", "NetatmoOutdoor", "Yard"],
        ),
    ],
)
def test_WeatherStationData_lastData(weatherStationData, station, exclude, expected):
    mod = weatherStationData.lastData(station, exclude)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod is expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, delay, expected",
    [
        (
            "MyStation",
            3600,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        (
            None,
            3600,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        (
            "",
            3600,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        pytest.param(
            "NoValidStation",
            3600,
            None,
            marks=pytest.mark.xfail(reason="Invalid station name not handled yet"),
        ),
    ],
)
def test_WeatherStationData_checkNotUpdated(
    weatherStationData, station, delay, expected
):
    mod = weatherStationData.checkNotUpdated(station, delay)
    assert sorted(mod) == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, delay, expected",
    [
        (
            "MyStation",
            798500,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        (
            None,
            798500,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
    ],
)
def test_WeatherStationData_checkUpdated(weatherStationData, station, delay, expected):
    mod = weatherStationData.checkUpdated(station, delay)
    assert sorted(mod) == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "device_id, scale, mtype, expected", [("MyStation", "scale", "type", [28.1])]
)
def test_WeatherStationData_getMeasure(
    weatherStationData, requests_mock, device_id, scale, mtype, expected
):
    with open("fixtures/weatherstation_measure.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.WeatherStation._GETMEASURE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        weatherStationData.getMeasure(device_id, scale, mtype)["body"]["1544558433"]
        == expected
    )
