"""Define tests for WeatherStation module."""
# pylint: disable=protected-access
import datetime as dt
import json

import pytest
import time_machine

import pyatmo


def test_weather_station_data(weather_station_data):
    assert (
        weather_station_data.stations["12:34:56:37:11:ca"]["station_name"]
        == "MyStation"
    )


def test_weather_station_data_no_response(auth, requests_mock):
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETSTATIONDATA_ENDPOINT,
        json={},
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        wsd = pyatmo.WeatherStationData(auth)
        wsd.update()


def test_weather_station_data_no_body(auth, requests_mock):
    with open("fixtures/status_ok.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETSTATIONDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        wsd = pyatmo.WeatherStationData(auth)
        wsd.update()


def test_weather_station_data_no_data(auth, requests_mock):
    with open("fixtures/home_data_empty.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETSTATIONDATA_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        wsd = pyatmo.WeatherStationData(auth)
        wsd.update()


@pytest.mark.parametrize(
    "station_id, expected",
    [
        (
            "12:34:56:37:11:ca",
            [
                "Garden",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Yard",
            ],
        ),
        ("12:34:56:36:fd:3c", ["Module", "NAMain", "Rain Gauge"]),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet.",
            ),
        ),
    ],
)
def test_weather_station_get_module_names(weather_station_data, station_id, expected):
    assert sorted(weather_station_data.get_module_names(station_id)) == expected


@pytest.mark.parametrize(
    "station_id, expected",
    [
        (None, {}),
        (
            "12:34:56:37:11:ca",
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
        (
            "12:34:56:1d:68:2e",
            {
                "12:34:56:1d:68:2e": {
                    "id": "12:34:56:1d:68:2e",
                    "module_name": "Basisstation",
                    "station_name": "NAMain",
                },
            },
        ),
        (
            "12:34:56:58:c8:54",
            {
                "12:34:56:58:c8:54": {
                    "id": "12:34:56:58:c8:54",
                    "module_name": "NAMain",
                    "station_name": "Njurunda (Indoor)",
                },
                "12:34:56:58:e6:38": {
                    "id": "12:34:56:58:e6:38",
                    "module_name": "NAModule1",
                    "station_name": "Njurunda (Indoor)",
                },
            },
        ),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet.",
            ),
        ),
    ],
)
def test_weather_station_get_modules(weather_station_data, station_id, expected):
    assert weather_station_data.get_modules(station_id) == expected


def test_weather_station_get_station(weather_station_data):
    result = weather_station_data.get_station("12:34:56:37:11:ca")

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

    assert weather_station_data.get_station("NoValidStation") == {}


@pytest.mark.parametrize(
    "mid, expected",
    [
        ("12:34:56:07:bb:3e", "12:34:56:07:bb:3e"),
        ("12:34:56:07:bb:3e", "12:34:56:07:bb:3e"),
        ("", {}),
        (None, {}),
    ],
)
def test_weather_station_get_module(weather_station_data, mid, expected):
    mod = weather_station_data.get_module(mid)

    assert isinstance(mod, dict)
    assert mod.get("_id", mod) == expected


@pytest.mark.parametrize(
    "module_id, expected",
    [
        (
            "12:34:56:07:bb:3e",
            [
                "CO2",
                "Humidity",
                "Temperature",
                "battery_percent",
                "battery_vp",
                "reachable",
                "rf_status",
                "temp_trend",
            ],
        ),
        (
            "12:34:56:07:bb:3e",
            [
                "CO2",
                "Humidity",
                "Temperature",
                "battery_percent",
                "battery_vp",
                "reachable",
                "rf_status",
                "temp_trend",
            ],
        ),
        (
            "12:34:56:03:1b:e4",
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
            "12:34:56:05:51:20",
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
            "12:34:56:37:11:ca",
            [
                "CO2",
                "Humidity",
                "Noise",
                "Pressure",
                "Temperature",
                "pressure_trend",
                "reachable",
                "temp_trend",
                "wifi_status",
            ],
        ),
        (
            "12:34:56:58:c8:54",
            [
                "CO2",
                "Humidity",
                "Noise",
                "Pressure",
                "Temperature",
                "pressure_trend",
                "reachable",
                "temp_trend",
                "wifi_status",
            ],
        ),
        (
            "12:34:56:58:e6:38",
            [
                "Humidity",
                "Temperature",
                "battery_percent",
                "battery_vp",
                "reachable",
                "rf_status",
                "temp_trend",
            ],
        ),
        pytest.param(
            None,
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
    ],
)
def test_weather_station_get_monitored_conditions(
    weather_station_data,
    module_id,
    expected,
):
    assert sorted(weather_station_data.get_monitored_conditions(module_id)) == expected


@time_machine.travel(dt.datetime(2019, 6, 11))
@pytest.mark.parametrize(
    "station_id, exclude, expected",
    [
        ("12:34:56:05:51:20", None, {}),
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
        ("", None, {}),
        ("NoValidStation", None, {}),
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
def test_weather_station_get_last_data(
    weather_station_data,
    station_id,
    exclude,
    expected,
):
    if mod := weather_station_data.get_last_data(station_id, exclude=exclude):
        assert sorted(mod) == expected
    else:
        assert mod == expected


@time_machine.travel(dt.datetime(2019, 6, 11))
@pytest.mark.parametrize(
    "station_id, delay, expected",
    [
        (
            "12:34:56:37:11:ca",
            3600,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:37:11:ca",
            ],
        ),
        ("12:34:56:37:11:ca", 798500, []),
        pytest.param(
            "NoValidStation",
            3600,
            None,
            marks=pytest.mark.xfail(reason="Invalid station name not handled yet"),
        ),
    ],
)
def test_weather_station_check_not_updated(
    weather_station_data,
    station_id,
    delay,
    expected,
):
    mod = weather_station_data.check_not_updated(station_id, delay)
    assert sorted(mod) == expected


@time_machine.travel(dt.datetime(2019, 6, 11))
@pytest.mark.parametrize(
    "station_id, delay, expected",
    [
        (
            "12:34:56:37:11:ca",
            798500,
            [
                "12:34:56:03:1b:e4",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:36:fc:de",
                "12:34:56:37:11:ca",
            ],
        ),
        ("12:34:56:37:11:ca", 100, []),
    ],
)
def test_weather_station_check_updated(
    weather_station_data,
    station_id,
    delay,
    expected,
):
    if mod := weather_station_data.check_updated(station_id, delay):
        assert sorted(mod) == expected
    else:
        assert mod == expected


@time_machine.travel(dt.datetime(2019, 6, 11))
@pytest.mark.parametrize(
    "device_id, scale, module_type, expected",
    [("MyStation", "scale", "type", [28.1])],
)
def test_weather_station_get_data(
    weather_station_data,
    requests_mock,
    device_id,
    scale,
    module_type,
    expected,
):
    with open("fixtures/weatherstation_measure.json", encoding="utf-8") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.const.DEFAULT_BASE_URL + pyatmo.const.GETMEASURE_ENDPOINT,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        weather_station_data.get_data(device_id, scale, module_type)["body"][
            "1544558433"
        ]
        == expected
    )


def test_weather_station_get_last_data_measurements(weather_station_data):
    station_id = "12:34:56:37:11:ca"
    module_id = "12:34:56:03:1b:e4"

    mod = weather_station_data.get_last_data(station_id, None)

    assert mod[station_id]["Temperature"] == 24.6
    assert mod[station_id]["Pressure"] == 1017.3
    assert mod[module_id]["WindAngle"] == 217
    assert mod[module_id]["WindStrength"] == 4
    assert mod[module_id]["GustAngle"] == 206
    assert mod[module_id]["GustStrength"] == 9


@time_machine.travel(dt.datetime(2019, 6, 11))
@pytest.mark.parametrize(
    "station_id, exclude, expected",
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
        (None, None, {}),
        ("12:34:56:00:aa:01", None, {}),
    ],
)
def test_weather_station_get_last_data_bug_97(
    weather_station_data,
    station_id,
    exclude,
    expected,
):
    if mod := weather_station_data.get_last_data(station_id, exclude):
        assert sorted(mod) == expected
    else:
        assert mod == expected
