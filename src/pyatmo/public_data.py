from pyatmo.exceptions import NoDevice
from pyatmo.helpers import BASE_URL, to_time_string

_GETPUBLIC_DATA = BASE_URL + "api/getpublicdata"
_LON_NE = 6.221652
_LAT_NE = 46.610870
_LON_SW = 6.217828
_LAT_SW = 46.596485

_STATION_TEMPERATURE_TYPE = "temperature"
_STATION_PRESSURE_TYPE = "pressure"
_STATION_HUMIDITY_TYPE = "humidity"

_ACCESSORY_RAIN_LIVE_TYPE = "rain_live"
_ACCESSORY_RAIN_60MIN_TYPE = "rain_60min"
_ACCESSORY_RAIN_24H_TYPE = "rain_24h"
_ACCESSORY_RAIN_TIME_TYPE = "rain_timeutc"
_ACCESSORY_WIND_STRENGTH_TYPE = "wind_strength"
_ACCESSORY_WIND_ANGLE_TYPE = "wind_angle"
_ACCESSORY_WIND_TIME_TYPE = "wind_timeutc"
_ACCESSORY_GUST_STRENGTH_TYPE = "gust_strength"
_ACCESSORY_GUST_ANGLE_TYPE = "gust_angle"


class PublicData:
    def __init__(
        self,
        authData,
        LAT_NE=_LAT_NE,
        LON_NE=_LON_NE,
        LAT_SW=_LAT_SW,
        LON_SW=_LON_SW,
        required_data_type=None,  # comma-separated list from above _STATION or _ACCESSORY values
        filtering=False,
    ):
        self.auth_data = authData
        post_params = {
            "lat_ne": LAT_NE,
            "lon_ne": LON_NE,
            "lat_sw": LAT_SW,
            "lon_sw": LON_SW,
            "filter": filtering,
        }

        if required_data_type:
            post_params["required_data"] = required_data_type

        resp = self.auth_data.post_request(url=_GETPUBLIC_DATA, params=post_params)
        try:
            self.raw_data = resp["body"]
        except (KeyError, TypeError):
            raise NoDevice("No public weather data returned by Netatmo server")
        self.status = resp["status"]
        self.time_exec = to_time_string(resp["time_exec"])
        self.time_server = to_time_string(resp["time_server"])

    def count_station_in_area(self):
        return len(self.raw_data)

    def get_latest_rain(self):
        return self.get_accessory_measures(_ACCESSORY_RAIN_LIVE_TYPE)

    def get_average_rain(self):
        return average_measure(self.get_latest_rain())

    def get_60min_rain(self):
        return self.get_accessory_measures(_ACCESSORY_RAIN_60MIN_TYPE)

    def get_average_60min_rain(self):
        return average_measure(self.get_60min_rain())

    def get_24h_rain(self):
        return self.get_accessory_measures(_ACCESSORY_RAIN_24H_TYPE)

    def get_average_24h_rain(self):
        return average_measure(self.get_24h_rain())

    def get_latest_pressures(self):
        return self.get_latest_station_measures(_STATION_PRESSURE_TYPE)

    def get_average_pressure(self):
        return average_measure(self.get_latest_pressures())

    def get_latest_temperatures(self):
        return self.get_latest_station_measures(_STATION_TEMPERATURE_TYPE)

    def get_average_temperature(self):
        return average_measure(self.get_latest_temperatures())

    def get_latest_humidities(self):
        return self.get_latest_station_measures(_STATION_HUMIDITY_TYPE)

    def get_average_humidity(self):
        return average_measure(self.get_latest_humidities())

    def get_latest_wind_strengths(self):
        return self.get_accessory_measures(_ACCESSORY_WIND_STRENGTH_TYPE)

    def get_average_wind_strength(self):
        return average_measure(self.get_latest_wind_strengths())

    def get_latest_wind_angles(self):
        return self.get_accessory_measures(_ACCESSORY_WIND_ANGLE_TYPE)

    def get_latest_gust_strengths(self):
        return self.get_accessory_measures(_ACCESSORY_GUST_STRENGTH_TYPE)

    def get_average_gust_strength(self):
        return average_measure(self.get_latest_gust_strengths())

    def get_latest_gust_angles(self):
        return self.get_accessory_measures(_ACCESSORY_GUST_ANGLE_TYPE)

    def get_locations(self):
        locations = {}
        for station in self.raw_data:
            locations[station["_id"]] = station["place"]["location"]
        return locations

    def get_time_for_rain_measures(self):
        return self.get_accessory_measures(_ACCESSORY_RAIN_TIME_TYPE)

    def get_time_for_wind_measures(self):
        return self.get_accessory_measures(_ACCESSORY_WIND_TIME_TYPE)

    def get_latest_station_measures(self, data_type):
        measures = {}
        for station in self.raw_data:
            for module in station["measures"].values():
                if (
                    "type" in module
                    and data_type in module["type"]
                    and "res" in module
                    and module["res"]
                ):
                    measure_index = module["type"].index(data_type)
                    latest_timestamp = sorted(module["res"], reverse=True)[0]
                    measures[station["_id"]] = module["res"][latest_timestamp][
                        measure_index
                    ]
        return measures

    def get_accessory_measures(self, data_type):
        measures = {}
        for station in self.raw_data:
            for module in station["measures"].values():
                if data_type in module:
                    measures[station["_id"]] = module[data_type]
        return measures


def average_measure(measures):
    if measures:
        return sum(measures.values()) / len(measures)
    return 0.0
