"""Define tests for weaather module."""

import pytest

import pyatmo
from pyatmo import DeviceType
from pyatmo.modules.base_class import Location, Place

# pylint: disable=F6401


@pytest.mark.asyncio()
async def test_async_weather_NAMain(async_home):  # pylint: disable=invalid-name
    """Test Netatmo weather station main module."""
    module_id = "12:34:56:80:bb:26"
    assert module_id in async_home.modules
    module = async_home.modules[module_id]
    assert module.device_type == DeviceType.NAMain


@pytest.mark.asyncio()
async def test_async_weather_update(async_account):
    """Test basic weather station update."""
    home_id = "91763b24c43d3e344f424e8b"
    await async_account.async_update_weather_stations()
    home = async_account.homes[home_id]

    module_id = "12:34:56:80:bb:26"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.device_type == DeviceType.NAMain
    assert module.name == "Villa"
    assert module.modules == [
        "12:34:56:80:44:92",
        "12:34:56:80:7e:18",
        "12:34:56:80:1c:42",
        "12:34:56:80:c1:ea",
    ]
    assert module.features == {
        "temperature",
        "humidity",
        "co2",
        "noise",
        "pressure",
        "absolute_pressure",
        "temp_trend",
        "pressure_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "wifi_strength",
        "place",
    }
    assert module.firmware_revision == 181
    assert module.wifi_strength == 57
    assert module.temperature == 21.1
    assert module.humidity == 45
    assert module.co2 == 1339
    assert module.pressure == 1026.8
    assert module.noise == 35
    assert module.absolute_pressure == 974.5
    assert module.place == Place(
        {
            "altitude": 329,
            "city": "Someplace",
            "country": "FR",
            "location": Location(longitude=6.1234567, latitude=46.123456),
            "timezone": "Europe/Paris",
        },
    )

    module_id = "12:34:56:80:44:92"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Bedroom"
    assert module.features == {
        "temperature",
        "temp_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "rf_strength",
        "co2",
        "humidity",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule4
    assert module.modules is None
    assert module.firmware_revision == 51
    assert module.rf_strength == 67
    assert module.temperature == 19.3
    assert module.humidity == 53
    assert module.battery == 28

    module_id = "12:34:56:80:c1:ea"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Rain"
    assert module.features == {
        "sum_rain_1",
        "sum_rain_24",
        "rain",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule3
    assert module.modules is None
    assert module.firmware_revision == 12
    assert module.rf_strength == 79
    assert module.rain == 3.7

    module_id = "12:34:56:80:1c:42"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Outdoor"
    assert module.features == {
        "temperature",
        "humidity",
        "temp_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule1
    assert module.modules is None
    assert module.firmware_revision == 50
    assert module.rf_strength == 68
    assert module.reachable is False

    module_id = "12:34:56:03:1b:e4"
    assert module_id in home.modules
    module = home.modules[module_id]
    assert module.name == "Villa Garden"
    assert module.features == {
        "wind_strength",
        "gust_strength",
        "gust_angle",
        "gust_direction",
        "wind_angle",
        "wind_direction",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.device_type == DeviceType.NAModule2
    assert module.modules is None
    assert module.firmware_revision == 19
    assert module.rf_strength == 59
    assert module.wind_strength == 4
    assert module.wind_angle == 217
    assert module.gust_strength == 9
    assert module.gust_angle == 206


@pytest.mark.asyncio()
async def test_async_weather_favorite(async_account):
    """Test favorite weather station."""
    await async_account.async_update_weather_stations()

    module_id = "00:11:22:2c:be:c8"
    assert module_id in async_account.modules
    module = async_account.modules[module_id]
    assert module.device_type == DeviceType.NAMain
    assert module.name == "Zuhause (Kinderzimmer)"
    assert module.modules == ["00:11:22:2c:ce:b6"]
    assert module.features == {
        "temperature",
        "humidity",
        "co2",
        "noise",
        "pressure",
        "absolute_pressure",
        "temp_trend",
        "pressure_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "wifi_strength",
        "place",
    }
    assert module.pressure == 1015.6
    assert module.absolute_pressure == 1000.4
    assert module.place == Place(
        {
            "altitude": 127,
            "city": "Wiesbaden",
            "country": "DE",
            "location": Location(
                longitude=8.238054275512695,
                latitude=50.07585525512695,
            ),
            "timezone": "Europe/Berlin",
        },
    )

    module_id = "00:11:22:2c:ce:b6"
    assert module_id in async_account.modules
    module = async_account.modules[module_id]
    assert module.device_type == DeviceType.NAModule1
    assert module.name == "Unknown"
    assert module.modules is None
    assert module.features == {
        "temperature",
        "humidity",
        "temp_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "reachable",
        "rf_strength",
        "battery",
        "place",
    }
    assert module.temperature == 7.8
    assert module.humidity == 87


@pytest.mark.asyncio()
async def test_async_air_care_update(async_account):
    """Test basic air care update."""
    await async_account.async_update_air_care()

    module_id = "12:34:56:26:68:92"
    assert module_id in async_account.modules
    module = async_account.modules[module_id]

    assert module.device_type == DeviceType.NHC
    assert module.name == "Baby Bedroom"
    assert module.features == {
        "temperature",
        "humidity",
        "co2",
        "noise",
        "pressure",
        "absolute_pressure",
        "temp_trend",
        "pressure_trend",
        "min_temp",
        "max_temp",
        "temp_max",
        "temp_min",
        "health_idx",
        "reachable",
        "wifi_strength",
        "place",
    }

    assert module.modules is None
    assert module.firmware_revision == 45
    assert module.wifi_strength == 68
    assert module.temperature == 21.6
    assert module.humidity == 66
    assert module.co2 == 1053
    assert module.pressure == 1021.4
    assert module.noise == 45
    assert module.absolute_pressure == 1011
    assert module.health_idx == 1


@pytest.mark.asyncio()
async def test_async_public_weather_update(async_account):
    """Test basic public weather update."""
    lon_ne = "6.221652"
    lat_ne = "46.610870"
    lon_sw = "6.217828"
    lat_sw = "46.596485"

    area_id = async_account.register_public_weather_area(lat_ne, lon_ne, lat_sw, lon_sw)
    await async_account.async_update_public_weather(area_id)

    area = async_account.public_weather_areas[area_id]
    assert area.location == pyatmo.modules.netatmo.Location(
        lat_ne,
        lon_ne,
        lat_sw,
        lon_sw,
    )
    assert area.stations_in_area() == 8

    assert area.get_latest_rain() == {
        "70:ee:50:1f:68:9e": 0,
        "70:ee:50:27:25:b0": 0,
        "70:ee:50:36:94:7c": 0.5,
        "70:ee:50:36:a9:fc": 0,
    }

    assert area.get_60_min_rain() == {
        "70:ee:50:1f:68:9e": 0,
        "70:ee:50:27:25:b0": 0,
        "70:ee:50:36:94:7c": 0.2,
        "70:ee:50:36:a9:fc": 0,
    }

    assert area.get_24_h_rain() == {
        "70:ee:50:1f:68:9e": 9.999,
        "70:ee:50:27:25:b0": 11.716000000000001,
        "70:ee:50:36:94:7c": 12.322000000000001,
        "70:ee:50:36:a9:fc": 11.009,
    }

    assert area.get_latest_pressures() == {
        "70:ee:50:1f:68:9e": 1007.3,
        "70:ee:50:27:25:b0": 1012.8,
        "70:ee:50:36:94:7c": 1010.6,
        "70:ee:50:36:a9:fc": 1010,
        "70:ee:50:01:20:fa": 1014.4,
        "70:ee:50:04:ed:7a": 1005.4,
        "70:ee:50:27:9f:2c": 1010.6,
        "70:ee:50:3c:02:78": 1011.7,
    }

    assert area.get_latest_temperatures() == {
        "70:ee:50:1f:68:9e": 21.1,
        "70:ee:50:27:25:b0": 23.2,
        "70:ee:50:36:94:7c": 21.4,
        "70:ee:50:36:a9:fc": 20.1,
        "70:ee:50:01:20:fa": 27.4,
        "70:ee:50:04:ed:7a": 19.8,
        "70:ee:50:27:9f:2c": 25.5,
        "70:ee:50:3c:02:78": 23.3,
    }

    assert area.get_latest_humidities() == {
        "70:ee:50:1f:68:9e": 69,
        "70:ee:50:27:25:b0": 60,
        "70:ee:50:36:94:7c": 62,
        "70:ee:50:36:a9:fc": 67,
        "70:ee:50:01:20:fa": 58,
        "70:ee:50:04:ed:7a": 76,
        "70:ee:50:27:9f:2c": 56,
        "70:ee:50:3c:02:78": 58,
    }

    assert area.get_latest_wind_strengths() == {"70:ee:50:36:a9:fc": 15}

    assert area.get_latest_wind_angles() == {"70:ee:50:36:a9:fc": 17}

    assert area.get_latest_gust_strengths() == {"70:ee:50:36:a9:fc": 31}

    assert area.get_latest_gust_angles() == {"70:ee:50:36:a9:fc": 217}
