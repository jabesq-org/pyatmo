"""Define tests for Public weather module."""
import json

import pytest

import smart_home.PublicData


def test_PublicData(auth, requests_mock):
    with open("fixtures/public_data_simple.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.PublicData._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    publicData = smart_home.PublicData.PublicData(auth)
    assert publicData.status == "ok"

    publicData = smart_home.PublicData.PublicData(
        auth, required_data_type="temperature,rain_live"
    )
    assert publicData.status == "ok"


def test_PublicData_unavailable(auth, requests_mock):
    requests_mock.post(smart_home.PublicData._GETPUBLIC_DATA, status_code=404)
    with pytest.raises(smart_home.PublicData.NoDevice):
        smart_home.PublicData.PublicData(auth)


def test_PublicData_error(auth, requests_mock):
    with open("fixtures/public_data_error_mongo.json") as f:
        json_fixture = json.load(f)
    requests_mock.post(
        smart_home.PublicData._GETPUBLIC_DATA,
        json=json_fixture,
        headers={"content-type": "application/json"},
    )
    with pytest.raises(smart_home.PublicData.NoDevice):
        smart_home.PublicData.PublicData(auth)


def test_PublicData_CountStationInArea(publicData):
    assert publicData.CountStationInArea() == 8


def test_PublicData_getLatestRain(publicData):
    expected = {
        "70:ee:50:1f:68:9e": 0,
        "70:ee:50:27:25:b0": 0,
        "70:ee:50:36:94:7c": 0.5,
        "70:ee:50:36:a9:fc": 0,
    }
    assert publicData.getLatestRain() == expected
    assert publicData.getLive() == expected


def test_PublicData_getAverageRain(publicData):
    assert publicData.getAverageRain() == 0.125


def test_PublicData_get60minRain(publicData):
    expected = {
        "70:ee:50:1f:68:9e": 0,
        "70:ee:50:27:25:b0": 0,
        "70:ee:50:36:94:7c": 0.2,
        "70:ee:50:36:a9:fc": 0,
    }
    assert publicData.get60min() == expected
    assert publicData.get60minRain() == expected


def test_PublicData_getAverage60minRain(publicData):
    assert publicData.getAverage60minRain() == 0.05


def test_PublicData_get24hRain(publicData):
    expected = {
        "70:ee:50:1f:68:9e": 9.999,
        "70:ee:50:27:25:b0": 11.716000000000001,
        "70:ee:50:36:94:7c": 12.322000000000001,
        "70:ee:50:36:a9:fc": 11.009,
    }
    assert publicData.get24h() == expected
    assert publicData.get24hRain() == expected


def test_PublicData_getAverage24hRain(publicData):
    assert publicData.getAverage24hRain() == 11.261500000000002


def test_PublicData_getLatestPressures(publicData):
    expected = {
        "70:ee:50:1f:68:9e": 1007.3,
        "70:ee:50:27:25:b0": 1012.8,
        "70:ee:50:36:94:7c": 1010.6,
        "70:ee:50:36:a9:fc": 1010,
        "70:ee:50:01:20:fa": 1014.4,
        "70:ee:50:04:ed:7a": 1005.4,
        "70:ee:50:27:9f:2c": 1010.6,
        "70:ee:50:3c:02:78": 1011.7,
    }
    assert publicData.getLatestPressures() == expected


def test_PublicData_getAveragePressure(publicData):
    assert publicData.getAveragePressure() == 1010.3499999999999


def test_PublicData_getLatestTemperatures(publicData):
    expected = {
        "70:ee:50:1f:68:9e": 21.1,
        "70:ee:50:27:25:b0": 23.2,
        "70:ee:50:36:94:7c": 21.4,
        "70:ee:50:36:a9:fc": 20.1,
        "70:ee:50:01:20:fa": 27.4,
        "70:ee:50:04:ed:7a": 19.8,
        "70:ee:50:27:9f:2c": 25.5,
        "70:ee:50:3c:02:78": 23.3,
    }
    assert publicData.getLatestTemperatures() == expected


def test_PublicData_getAverageTemperature(publicData):
    assert publicData.getAverageTemperature() == 22.725


def test_PublicData_getLatestHumidities(publicData):
    expected = {
        "70:ee:50:1f:68:9e": 69,
        "70:ee:50:27:25:b0": 60,
        "70:ee:50:36:94:7c": 62,
        "70:ee:50:36:a9:fc": 67,
        "70:ee:50:01:20:fa": 58,
        "70:ee:50:04:ed:7a": 76,
        "70:ee:50:27:9f:2c": 56,
        "70:ee:50:3c:02:78": 58,
    }
    assert publicData.getLatestHumidities() == expected


def test_PublicData_getAverageHumidity(publicData):
    assert publicData.getAverageHumidity() == 63.25


def test_PublicData_getLatestWindStrengths(publicData):
    expected = {"70:ee:50:36:a9:fc": 15}
    assert publicData.getLatestWindStrengths() == expected


def test_PublicData_getAverageWindStrength(publicData):
    assert publicData.getAverageWindStrength() == 15


def test_PublicData_getLatestWindAngles(publicData):
    expected = {"70:ee:50:36:a9:fc": 17}
    assert publicData.getLatestWindAngles() == expected


def test_PublicData_getLatestGustStrengths(publicData):
    expected = {"70:ee:50:36:a9:fc": 31}
    assert publicData.getLatestGustStrengths() == expected


def test_PublicData_getAverageGustStrength(publicData):
    assert publicData.getAverageGustStrength() == 31


def test_PublicData_getLatestGustAngles(publicData):
    expected = {"70:ee:50:36:a9:fc": 217}
    assert publicData.getLatestGustAngles() == expected


def test_PublicData_getLocations(publicData):
    expected = {
        "70:ee:50:1f:68:9e": [8.795445200000017, 50.2130169],
        "70:ee:50:27:25:b0": [8.7807159, 50.1946167],
        "70:ee:50:36:94:7c": [8.791382999999996, 50.2136394],
        "70:ee:50:36:a9:fc": [8.801164269110814, 50.19596181704958],
        "70:ee:50:01:20:fa": [8.7953, 50.195241],
        "70:ee:50:04:ed:7a": [8.785034, 50.192169],
        "70:ee:50:27:9f:2c": [8.785342, 50.193573],
        "70:ee:50:3c:02:78": [8.795953681700666, 50.19530139868166],
    }
    assert publicData.getLocations() == expected


def test_PublicData_getTimeforMeasure(publicData):
    expected = {
        "70:ee:50:36:a9:fc": 1560248184,
        "70:ee:50:1f:68:9e": 1560248344,
        "70:ee:50:27:25:b0": 1560247896,
        "70:ee:50:36:94:7c": 1560248022,
    }
    assert publicData.getTimeforMeasure() == expected
    assert publicData.getTimeForRainMeasures() == expected


def test_PublicData_getTimeForWindMeasures(publicData):
    expected = {"70:ee:50:36:a9:fc": 1560248190}
    assert publicData.getTimeForWindMeasures() == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            "pressure",
            {
                "70:ee:50:01:20:fa": 1014.4,
                "70:ee:50:04:ed:7a": 1005.4,
                "70:ee:50:1f:68:9e": 1007.3,
                "70:ee:50:27:25:b0": 1012.8,
                "70:ee:50:27:9f:2c": 1010.6,
                "70:ee:50:36:94:7c": 1010.6,
                "70:ee:50:36:a9:fc": 1010,
                "70:ee:50:3c:02:78": 1011.7,
            },
        ),
        (
            "temperature",
            {
                "70:ee:50:01:20:fa": 27.4,
                "70:ee:50:04:ed:7a": 19.8,
                "70:ee:50:1f:68:9e": 21.1,
                "70:ee:50:27:25:b0": 23.2,
                "70:ee:50:27:9f:2c": 25.5,
                "70:ee:50:36:94:7c": 21.4,
                "70:ee:50:36:a9:fc": 20.1,
                "70:ee:50:3c:02:78": 23.3,
            },
        ),
        (
            "humidity",
            {
                "70:ee:50:01:20:fa": 58,
                "70:ee:50:04:ed:7a": 76,
                "70:ee:50:1f:68:9e": 69,
                "70:ee:50:27:25:b0": 60,
                "70:ee:50:27:9f:2c": 56,
                "70:ee:50:36:94:7c": 62,
                "70:ee:50:36:a9:fc": 67,
                "70:ee:50:3c:02:78": 58,
            },
        ),
    ],
)
def test_PublicData_getLatestStationMeasures(publicData, test_input, expected):
    assert publicData.getLatestStationMeasures(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("wind_strength", {"70:ee:50:36:a9:fc": 15}),
        ("wind_angle", {"70:ee:50:36:a9:fc": 17}),
        ("gust_strength", {"70:ee:50:36:a9:fc": 31}),
        ("gust_angle", {"70:ee:50:36:a9:fc": 217}),
        ("wind_timeutc", {"70:ee:50:36:a9:fc": 1560248190}),
    ],
)
def test_PublicData_getAccessoryMeasures(publicData, test_input, expected):
    assert publicData.getAccessoryMeasures(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            {
                "70:ee:50:01:20:fa": 1014.4,
                "70:ee:50:04:ed:7a": 1005.4,
                "70:ee:50:1f:68:9e": 1007.3,
                "70:ee:50:27:25:b0": 1012.8,
                "70:ee:50:27:9f:2c": 1010.6,
                "70:ee:50:36:94:7c": 1010.6,
                "70:ee:50:36:a9:fc": 1010,
                "70:ee:50:3c:02:78": 1011.7,
            },
            1010.35,
        ),
        (
            {
                "70:ee:50:01:20:fa": 27.4,
                "70:ee:50:04:ed:7a": 19.8,
                "70:ee:50:1f:68:9e": 21.1,
                "70:ee:50:27:25:b0": 23.2,
                "70:ee:50:27:9f:2c": 25.5,
                "70:ee:50:36:94:7c": 21.4,
                "70:ee:50:36:a9:fc": 20.1,
                "70:ee:50:3c:02:78": 23.3,
            },
            22.725,
        ),
        ({}, 0),
    ],
)
def test_PublicData_averageMeasure(test_input, expected):
    assert smart_home.PublicData.averageMeasure(test_input) == expected
