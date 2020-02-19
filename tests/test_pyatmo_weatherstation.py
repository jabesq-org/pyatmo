"""Define tests for WeatherStation module."""
# pylint: disable=protected-access
import json

import pytest
from freezegun import freeze_time

import pyatmo


def test_weather_station_data(weather_station_data):
    assert weather_station_data.default_station == "MyStation"


def test_weather_station_data_no_response(auth, requests_mock):
    requests_mock.post(pyatmo.weather_station._GETSTATIONDATA_REQ, text="None")
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.WeatherStationData(auth)


def test_weather_station_data_no_body(auth, requests_mock):
    with open("fixtures/status_ok.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.weather_station._GETSTATIONDATA_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(pyatmo.NoDevice):
        assert pyatmo.WeatherStationData(auth)


def test_weather_station_data_no_data(auth, requests_mock):
    with open("fixtures/home_data_empty.json") as json_file:
        json_fixture = json.load(json_file)
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
                "Indoor",
                "Inne - Nere",
                "Inne - Uppe",
                "Kitchen",
                "Livingroom",
                "Module",
                "NAMain",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Regnmätare",
                "Ute",
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
        ("Valley Road", ["Module", "NAMain", "Rain Gauge"],),
        pytest.param(
            "NoValidStation",
            None,
            marks=pytest.mark.xfail(
                reason="Invalid station names are not handled yet."
            ),
        ),
    ],
)
def test_weather_station_data_modules_names_list(
    weather_station_data, station, expected
):
    assert sorted(weather_station_data.modules_names_list(station)) == expected


@pytest.mark.parametrize(
    "station, expected",
    [
        (
            None,
            {
                "12:34:56:02:b3:da": {
                    "id": "12:34:56:02:b3:da",
                    "module_name": "Regnmätare",
                    "station_name": "Bolås",
                },
                "12:34:56:03:1b:e4": {
                    "id": "12:34:56:03:1b:e4",
                    "module_name": "Garden",
                    "station_name": "MyStation",
                },
                "12:34:56:03:76:60": {
                    "id": "12:34:56:03:76:60",
                    "module_name": "Inne - Uppe",
                    "station_name": "Bolås",
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
                "12:34:56:1c:68:2e": {
                    "id": "12:34:56:1c:68:2e",
                    "module_name": "Inne - Nere",
                    "station_name": "Bolås",
                },
                "12:34:56:32:a7:60": {
                    "id": "12:34:56:32:a7:60",
                    "module_name": "Indoor",
                    "station_name": "Ateljen",
                },
                "12:34:56:32:db:06": {
                    "id": "12:34:56:32:db:06",
                    "module_name": "Ute",
                    "station_name": "Bolås",
                },
                "12:34:56:36:e6:c0": {
                    "id": "12:34:56:36:e6:c0",
                    "module_name": "Module",
                    "station_name": "Valley Road",
                },
                "12:34:56:36:fd:3c": {
                    "id": "12:34:56:36:fd:3c",
                    "module_name": "NAMain",
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
def test_weather_station_data_get_modules(weather_station_data, station, expected):
    assert weather_station_data.get_modules(station) == expected


def test_weather_station_data_station_by_name(weather_station_data):
    result = weather_station_data.station_by_name()
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
    assert weather_station_data.station_by_name("NoValidStation") is None


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
def test_weather_station_data_module_by_name(
    weather_station_data, module, station, expected
):
    mod = weather_station_data.module_by_name(module, station)
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
def test_weather_station_data_module_by_id(weather_station_data, mid, sid, expected):
    mod = weather_station_data.module_by_id(mid, sid)
    if mod:
        assert mod["_id"] == expected
    else:
        assert mod is expected


@pytest.mark.parametrize(
    "module, module_id, expected",
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
def test_weather_station_data_monitored_conditions(
    weather_station_data, module, module_id, expected
):
    assert (
        sorted(
            weather_station_data.monitored_conditions(
                module=module, module_id=module_id
            )
        )
        == expected
    )


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "station, exclude, by_id, expected",
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
                "Indoor",
                "Inne - Nere",
                "Inne - Uppe",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Regnmätare",
                "Ute",
                "Yard",
            ],
        ),
        (
            None,
            798103,
            False,
            [
                "Garden",
                "Indoor",
                "Inne - Nere",
                "Inne - Uppe",
                "Kitchen",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Regnmätare",
                "Ute",
                "Yard",
            ],
        ),
        (
            None,
            798103,
            True,
            [
                "12:34:56:02:b3:da",
                "12:34:56:03:1b:e4",
                "12:34:56:03:76:60",
                "12:34:56:05:25:6e",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:3e",
                "12:34:56:1c:68:2e",
                "12:34:56:32:a7:60",
                "12:34:56:32:db:06",
                "12:34:56:36:fc:de",
                "12:34:56:36:fd:3c",
                "12:34:56:37:11:ca",
            ],
        ),
    ],
)
def test_weather_station_data_last_data(
    weather_station_data, station, exclude, by_id, expected
):
    mod = weather_station_data.last_data(station=station, exclude=exclude, by_id=by_id)
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
def test_weather_station_data_last_data_by_id(
    weather_station_data, station, exclude, expected
):
    mod = weather_station_data.last_data(station, exclude, by_id=True)
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
def test_weather_station_data_check_not_updated(
    weather_station_data, station, delay, expected
):
    mod = weather_station_data.check_not_updated(station, delay)
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
                "Indoor",
                "Inne - Nere",
                "Inne - Uppe",
                "Kitchen",
                "Livingroom",
                "NetatmoIndoor",
                "NetatmoOutdoor",
                "Rain Gauge",
                "Regnmätare",
                "Ute",
                "Yard",
            ],
        ),
    ],
)
def test_weather_station_data_check_updated(
    weather_station_data, station, delay, expected
):
    mod = weather_station_data.check_updated(station, delay)
    assert sorted(mod) == expected


@freeze_time("2019-06-11")
@pytest.mark.parametrize(
    "device_id, scale, mtype, expected", [("MyStation", "scale", "type", [28.1])]
)
def test_weather_station_data_get_measure(
    weather_station_data, requests_mock, device_id, scale, mtype, expected
):
    with open("fixtures/weatherstation_measure.json") as json_file:
        json_fixture = json.load(json_file)
    requests_mock.post(
        pyatmo.weather_station._GETMEASURE_REQ,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    assert (
        weather_station_data.get_measure(device_id, scale, mtype)["body"]["1544558433"]
        == expected
    )


def test_weather_station_data_last_data_measurements(weather_station_data):
    mod = weather_station_data.last_data("MyStation", None)
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
                "12:34:56:02:b3:da",
                "12:34:56:03:1b:e4",
                "12:34:56:03:76:60",
                "12:34:56:05:25:6e",
                "12:34:56:05:51:20",
                "12:34:56:07:bb:0e",
                "12:34:56:07:bb:3e",
                "12:34:56:1c:68:2e",
                "12:34:56:32:a7:60",
                "12:34:56:32:db:06",
                "12:34:56:36:fc:de",
                "12:34:56:36:fd:3c",
                "12:34:56:37:11:ca",
            ],
        ),
        ("12:34:56:00:aa:01", None, {}),
    ],
)
def test_weather_station_data_last_data_bug_97(
    weather_station_data, station, exclude, expected
):
    mod = weather_station_data.last_data(station, exclude, by_id=True)
    if mod:
        assert sorted(mod) == expected
    else:
        assert mod == expected
