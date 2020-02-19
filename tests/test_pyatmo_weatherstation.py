"""Define tests for WeatherStation module."""
import json

import pytest
from freezegun import freeze_time

import pyatmo


def test_WeatherStationData(weatherStationData):
    assert weatherStationData.default_station == "MyStation"


def test_WeatherStationData_no_response(auth, requests_mock):
    requests_mock.post(pyatmo.weather_station._GETSTATIONDATA_REQ, text="None")
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.WeatherStationData(auth)


def test_WeatherStationData_no_body(auth, requests_mock):
    with open("fixtures/status_ok.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.weather_station._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.WeatherStationData(auth)


def test_WeatherStationData_no_data(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        pyatmo.weather_station._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.WeatherStationData(auth)


@pytest.mark.parametrize(
    "station, expected",
    [
        (
            None,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "Module",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Station",
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


@pytest.mark.parametrize(
    "station, expected",
    [
        (
            None,
            {
                "12:34:56:03:1b:e4": {
                    "id": "12:34:56:03:1b:e4",
                    "module_name": "Garden",
                    "station_name": "MyStation",
                },
                "12:34:56:05:51:20": {
                    "id": "12:34:56:05:51:20",
                    "module_name": "Yard",
                    "station_name": "MyStation",
                },
                "12:34:56:07:bb:0e": {
                    "id": "12:34:56:07:bb:0e",
                    "module_name": "Livingroom",
                    "station_name": "MyStation",
                },
                "12:34:56:07:bb:3e": {
                    "id": "12:34:56:07:bb:3e",
                    "module_name": "Kitchen",
                    "station_name": "MyStation",
                },
                "12:34:56:36:fc:de": {
                    "id": "12:34:56:36:fc:de",
                    "module_name": "NetatmoOutdoor",
                    "station_name": "MyStation",
                },
                "12:34:56:37:11:ca": {
                    "id": "12:34:56:37:11:ca",
                    "module_name": "NetatmoIndoor",
                    "station_name": "MyStation",
                },
                "12:34:56:36:e6:c0": {
                    "id": "12:34:56:36:e6:c0",
                    "module_name": "Module",
                    "station_name": "Valley Road",
                },
                "12:34:56:36:fd:3c": {
                    "id": "12:34:56:36:fd:3c",
                    "module_name": "Station",
                    "station_name": "Valley Road",
                },
                "12:34:56:05:25:6e": {
                    "id": "12:34:56:05:25:6e",
                    "module_name": "Rain Gauge",
                    "station_name": "Valley Road",
                },
            },
        ),
        (
            "MyStation",
            {
                "12:34:56:03:1b:e4": {
                    "id": "12:34:56:03:1b:e4",
                    "module_name": "Garden",
                    "station_name": "MyStation",
                },
                "12:34:56:05:51:20": {
                    "id": "12:34:56:05:51:20",
                    "module_name": "Yard",
                    "station_name": "MyStation",
                },
                "12:34:56:07:bb:0e": {
                    "id": "12:34:56:07:bb:0e",
                    "module_name": "Livingroom",
                    "station_name": "MyStation",
                },
                "12:34:56:07:bb:3e": {
                    "id": "12:34:56:07:bb:3e",
                    "module_name": "Kitchen",
                    "station_name": "MyStation",
                },
                "12:34:56:36:fc:de": {
                    "id": "12:34:56:36:fc:de",
                    "module_name": "NetatmoOutdoor",
                    "station_name": "MyStation",
                },
                "12:34:56:37:11:ca": {
                    "id": "12:34:56:37:11:ca",
                    "module_name": "NetatmoIndoor",
                    "station_name": "MyStation",
                },
            },
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
def test_WeatherStationData_getModules(weatherStationData, station, expected):
    assert weatherStationData.getModules(station) == expected


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
    "module, moduleId, expected",
    [
        (
            None,
            "12:34:56:07:bb:3e",
            [
                "CO2",
                "Humidity",
                "Temperature",
                "battery_percent",
                "battery_vp",
                "max_temp",
                "min_temp",
                "reachable",
                "rf_status",
            ],
        ),
        (
            "Kitchen",
            None,
            [
                "CO2",
                "Humidity",
                "Temperature",
                "battery_percent",
                "battery_vp",
                "max_temp",
                "min_temp",
                "reachable",
                "rf_status",
            ],
        ),
        (
            "Garden",
            None,
            [
                "GustAngle",
                "GustStrength",
                "WindAngle",
                "WindStrength",
                "battery_percent",
                "battery_vp",
                "reachable",
                "rf_status",
            ],
        ),
        (
            "Yard",
            None,
            [
                "Rain",
                "battery_percent",
                "battery_vp",
                "reachable",
                "rf_status",
                "sum_rain_1",
                "sum_rain_24",
            ],
        ),
        (
            "NetatmoIndoor",
            None,
            [
                "CO2",
                "Humidity",
                "Noise",
                "Pressure",
                "Temperature",
                "max_temp",
                "min_temp",
                "reachable",
                "wifi_status",
            ],
        ),
        pytest.param(
            "12:34:56:07:bb:3e",
            None,
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
        pytest.param(
            "",
            None,
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
        pytest.param(
            None,
            None,
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
    ],
)
def test_WeatherStationData_monitoredConditions(
    weatherStationData, module, moduleId, expected
):
    assert (
        sorted(weatherStationData.monitoredConditions(module=module, moduleId=moduleId))
        == expected
    )


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, exclude, byId, expected",
    [
        (
            "MyStation",
            None,
            False,
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
            False,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        ("NoValidStation", None, False, {}),
        (
            None,
            1000000,
            False,
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Yard",
            ],
        ),
        (
            None,
            798103,
            False,
            [
                "Garden",
                "Kitchen",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Yard",
            ],
        ),
        (
            None,
            798103,
            True,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:25:6e",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:36:fd:3c",
                "12:34:56:37:11:ca",
            ],
        ),
    ],
)
def test_WeatherStationData_lastData(
    weatherStationData, station, exclude, byId, expected
):
    mod = weatherStationData.lastData(station=station, exclude=exclude, byId=byId)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, exclude, expected",
    [
        (
            "12:34:56:37:11:ca",
            None,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:37:11:ca",
            ],
        ),
        ("", None, {},),
        ("NoValidStation", None, {},),
        (
            "12:34:56:37:11:ca",
            1000000,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:37:11:ca",
            ],
        ),
        (
            "12:34:56:37:11:ca",
            798103,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:37:11:ca",
            ],
        ),
    ],
)
def test_WeatherStationData_lastData_byId(
    weatherStationData, station, exclude, expected
):
    mod = weatherStationData.lastData(station, exclude, byId=True)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected


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
                "Rain Gauge",
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
        pyatmo.weather_station._GETMEASURE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        weatherStationData.getMeasure(device_id, scale, mtype)["body"]["1544558433"]
        == expected
    )


def test_WeatherStationData_lastData_measurements(weatherStationData):
    mod = weatherStationData.lastData("MyStation", None)
    assert mod["NetatmoIndoor"]["min_temp"] == 23.4
    assert mod["NetatmoIndoor"]["max_temp"] == 25.6
    assert mod["NetatmoIndoor"]["Temperature"] == 24.6
    assert mod["NetatmoIndoor"]["Pressure"] == 1017.3
    assert mod["Garden"]["WindAngle"] == 217
    assert mod["Garden"]["WindStrength"] == 4
    assert mod["Garden"]["GustAngle"] == 206
    assert mod["Garden"]["GustStrength"] == 9


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, exclude, expected",
    [
        (
            "12:34:56:37:11:ca",
            None,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:37:11:ca",
            ],
        ),
        (
            None,
            None,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:25:6e",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:36:fd:3c",
                "12:34:56:37:11:ca",
            ],
        ),
        ("12:34:56:00:aa:01", None, {},),
    ],
)
def test_WeatherStationData_lastData_bug_97(
    weatherStationData, station, exclude, expected
):
    mod = weatherStationData.lastData(station, exclude, byId=True)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected
