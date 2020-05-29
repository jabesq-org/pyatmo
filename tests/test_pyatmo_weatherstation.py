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
        ("12:34:56:36:fd:3c", ["Module", "NAMain", "Rain Gauge"],),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet."
            ),
        ),
    ],
)
def test_WeatherStationData_get_module_names(weatherStationData, station_id, expected):
    assert sorted(weatherStationData.get_module_names(station_id)) == expected


@pytest.mark.parametrize(
    "station_id, expected",
    [
        (None, {},),
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
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet."
            ),
        ),
    ],
)
def test_WeatherStationData_get_modules(weatherStationData, station_id, expected):
    assert weatherStationData.get_modules(station_id) == expected


def test_WeatherStationData_get_station(weatherStationData):
    result = weatherStationData.get_station("12:34:56:37:11:ca")

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

    assert weatherStationData.get_station("NoValidStation") == {}


@pytest.mark.parametrize(
    "mid, sid, expected",
    [
        ("12:34:56:07:bb:3e", None, "12:34:56:07:bb:3e"),
        ("12:34:56:07:bb:3e", "12:34:56:37:11:ca", "12:34:56:07:bb:3e"),
        ("", None, {}),
        ("", "", {}),
        (None, None, {}),
    ],
)
def test_WeatherStationData_get_module(weatherStationData, mid, sid, expected):
    mod = weatherStationData.get_module(mid, sid)

    assert type(mod) == dict
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
                "max_temp",
                "min_temp",
                "reachable",
                "rf_status",
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
                "max_temp",
                "min_temp",
                "reachable",
                "rf_status",
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
                "max_temp",
                "min_temp",
                "reachable",
                "wifi_status",
            ],
        ),
        pytest.param(
            None,
            None,
            marks=pytest.mark.xfail(reason="Invalid module names are not handled yet."),
        ),
    ],
)
def test_WeatherStationData_get_monitored_conditions(
    weatherStationData, module_id, expected
):
    assert sorted(weatherStationData.get_monitored_conditions(module_id)) == expected


# @freeze_time("2019-06-11")
# @pytest.mark.parametrize(
#     "station_id, exclude, expected",
#     [
#         (
#             "12:34:56:05:51:20",
#             None,
#             [
#                 "Garden",
#                 "Kitchen",
#                 "Livingroom",
#                 "NetatmoIndoor",
#                 "NetatmoOutdoor",
#                 "Yard",
#             ],
#         ),
#         (
#             "12:34:56:37:11:ca",
#             798103,
#             [
#                 "12:34:56:02:b3:da",
#                 "12:34:56:03:1b:e4",
#                 "12:34:56:03:76:60",
#                 "12:34:56:05:25:6e",
#                 "12:34:56:05:51:20",
#                 "12:34:56:07:bb:3e",
#                 "12:34:56:1c:68:2e",
#                 "12:34:56:32:a7:60",
#                 "12:34:56:32:db:06",
#                 "12:34:56:36:fc:de",
#                 "12:34:56:36:fd:3c",
#                 "12:34:56:37:11:ca",
#             ],
#         ),
#     ],
# )
# def test_WeatherStationData_get_last_data(
#     weatherStationData, station_id, exclude, expected
# ):
#     mod = weatherStationData.get_last_data(station_id, exclude=exclude)
#     if mod:
#         assert sorted(mod) == expected
#     else:
#         assert mod == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station_id, exclude, expected",
    [
        ("12:34:56:05:51:20", None, {},),
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
def test_WeatherStationData_get_last_data(
    weatherStationData, station_id, exclude, expected
):
    mod = weatherStationData.get_last_data(station_id, exclude=exclude)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected


@freeze_time("2019-06-11")
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
        ("12:34:56:37:11:ca", 798500, [],),
        pytest.param(
            "NoValidStation",
            3600,
            None,
            marks=pytest.mark.xfail(reason="Invalid station name not handled yet"),
        ),
    ],
)
def test_WeatherStationData_check_not_updated(
    weatherStationData, station_id, delay, expected
):
    mod = weatherStationData.check_not_updated(station_id, delay)
    assert sorted(mod) == expected


@freeze_time("2019-06-11")
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
        ("12:34:56:37:11:ca", 100, [],),
    ],
)
def test_WeatherStationData_check_updated(
    weatherStationData, station_id, delay, expected
):
    mod = weatherStationData.check_updated(station_id, delay)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "device_id, scale, mtype, expected", [("MyStation", "scale", "type", [28.1])]
)
def test_WeatherStationData_get_measure(
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
        weatherStationData.get_measure(device_id, scale, mtype)["body"]["1544558433"]
        == expected
    )


def test_WeatherStationData_get_last_data_measurements(weatherStationData):
    station_id = "12:34:56:37:11:ca"
    module_id = "12:34:56:03:1b:e4"

    mod = weatherStationData.get_last_data(station_id, None)

    assert mod[station_id]["min_temp"] == 23.4
    assert mod[station_id]["max_temp"] == 25.6
    assert mod[station_id]["Temperature"] == 24.6
    assert mod[station_id]["Pressure"] == 1017.3
    assert mod[module_id]["WindAngle"] == 217
    assert mod[module_id]["WindStrength"] == 4
    assert mod[module_id]["GustAngle"] == 206
    assert mod[module_id]["GustStrength"] == 9


@freeze_time("2019-06-11")
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
        (None, None, {},),
        ("12:34:56:00:aa:01", None, {},),
    ],
)
def test_WeatherStationData_get_last_data_bug_97(
    weatherStationData, station_id, exclude, expected
):
    mod = weatherStationData.get_last_data(station_id, exclude)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected
