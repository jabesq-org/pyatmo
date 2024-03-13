"""Module to represent a Netatmo module."""
from __future__ import annotations

import copy
from datetime import datetime, timezone, timedelta
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientConnectorError

from pyatmo.const import GETMEASURE_ENDPOINT, RawData, MeasureInterval, ENERGY_ELEC_PEAK_IDX, \
    MEASURE_INTERVAL_TO_SECONDS
from pyatmo.exceptions import ApiError
from pyatmo.modules.base_class import EntityBase, NetatmoBase, Place
from pyatmo.modules.device_types import DEVICE_CATEGORY_MAP, DeviceCategory, DeviceType

if TYPE_CHECKING:
    from pyatmo.event import Event
    from pyatmo.home import Home


import bisect
from operator import itemgetter

LOG = logging.getLogger(__name__)

ModuleT = dict[str, Any]

# Hide from features list
ATTRIBUTE_FILTER = {
    "battery_state",
    "battery_level",
    "battery_percent",
    "date_min_temp",
    "date_max_temp",
    "name",
    "entity_id",
    "device_id",
    "modules",
    "firmware_revision",
    "firmware_name",
    "home",
    "bridge",
    "room_id",
    "device_category",
    "device_type",
    "features",
}


def process_battery_state(data: str) -> int:
    """Process battery data and return percent (int) for display."""

    mapping = {
        "max": 100,
        "full": 90,
        "high": 75,
        "medium": 50,
        "low": 25,
        "very_low": 10,
    }
    return mapping[data]


class FirmwareMixin(EntityBase):
    """Mixin for firmware data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize firmware mixin."""
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.firmware_revision: int | None = None
        self.firmware_name: str | None = None


class WifiMixin(EntityBase):
    """Mixin for wifi data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize wifi mixin."""
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.wifi_strength: int | None = None


class RfMixin(EntityBase):
    """Mixin for rf data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize rf mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.rf_strength: int | None = None


class RainMixin(EntityBase):
    """Mixin for rain data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize rain mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.rain: float | None = None
        self.sum_rain_1: float | None = None
        self.sum_rain_24: float | None = None


class WindMixin(EntityBase):
    """Mixin for wind data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize wind mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.wind_strength: int | None = None
        self.wind_angle: int | None = None
        self.gust_strength: int | None = None
        self.gust_angle: int | None = None

    @property
    def wind_direction(self) -> str | None:
        """Return wind direction."""

        return None if self.wind_angle is None else process_angle(self.wind_angle)

    @property
    def gust_direction(self) -> str | None:
        """Return gust direction."""

        return None if self.gust_angle is None else process_angle(self.gust_angle)


def process_angle(angle: int) -> str:
    """Process angle and return string for display."""

    if angle >= 330:
        return "N"
    if angle >= 300:
        return "NW"
    if angle >= 240:
        return "W"
    if angle >= 210:
        return "SW"
    if angle >= 150:
        return "S"
    if angle >= 120:
        return "SE"
    if angle >= 60:
        return "E"
    return "NE" if angle >= 30 else "N"


class TemperatureMixin(EntityBase):
    """Mixin for temperature data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize temperature mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.temperature: float | None = None
        self.temp_min: float | None = None
        self.temp_max: float | None = None
        self.temp_trend: str | None = None
        self.min_temp: float | None = None
        self.max_temp: float | None = None
        self.date_min_temp: int | None = None
        self.date_max_temp: int | None = None


class HumidityMixin(EntityBase):
    """Mixin for humidity data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize humidity mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.humidity: int | None = None


class CO2Mixin(EntityBase):
    """Mixin for CO2 data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize CO2 mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.co2: int | None = None


class HealthIndexMixin(EntityBase):
    """Mixin for health index data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize health index mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.health_idx: int | None = None


class NoiseMixin(EntityBase):
    """Mixin for noise data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize noise mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.noise: int | None = None


class PressureMixin(EntityBase):
    """Mixin for pressure data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize pressure mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.pressure: float | None = None
        self.absolute_pressure: float | None = None
        self.pressure_trend: str | None = None


class BoilerMixin(EntityBase):
    """Mixin for boiler data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize boiler mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.boiler_status: bool | None = None


class BatteryMixin(EntityBase):
    """Mixin for battery data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize battery mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.battery_state: str | None = None
        self.battery_level: int | None = None
        self.battery_percent: int | None = None

    @property
    def battery(self) -> int:
        """Return battery percent."""

        if self.battery_percent is not None:
            return self.battery_percent
        if self.battery_state is None:
            return 0
        return process_battery_state(self.battery_state)


class PlaceMixin(EntityBase):
    """Mixin for place data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize place mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.place: Place | None = None


class DimmableMixin(EntityBase):
    """Mixin for dimmable data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize dimmable mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.brightness: int | None = None

    async def async_set_brightness(self, brightness: int) -> bool:
        """Set brightness."""

        json_brightness = {
            "modules": [
                {
                    "id": self.entity_id,
                    "brightness": max(min(100, brightness), -1),
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_brightness)


class ApplianceTypeMixin(EntityBase):
    """Mixin for appliance type data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize appliance type mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.appliance_type: str | None = None


class PowerMixin(EntityBase):
    """Mixin for power data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize power mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.power: int | None = None


class EventMixin(EntityBase):
    """Mixin for event data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize event mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.events: list[Event] = []


class ContactorMixin(EntityBase):
    """Mixin for contactor data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize contactor mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.contactor_mode: str | None = None


class OffloadMixin(EntityBase):
    """Mixin for offload data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize offload mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.offload: bool | None = None


class SwitchMixin(EntityBase):
    """Mixin for switch data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize switch mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.on: bool | None = None

    async def async_set_switch(self, target_position: int) -> bool:
        """Set switch to target position."""

        json_switch = {
            "modules": [
                {
                    "id": self.entity_id,
                    "on": target_position,
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_switch)

    async def async_on(self) -> bool:
        """Switch on."""

        return await self.async_set_switch(True)

    async def async_off(self) -> bool:
        """Switch off."""

        return await self.async_set_switch(False)


class FanSpeedMixin(EntityBase):
    """Mixin for fan speed data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize fan speed mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.fan_speed: int | None = None

    async def async_set_fan_speed(self, speed: int) -> bool:
        """Set fan speed."""

        json_fan_speed = {
            "modules": [
                {
                    "id": self.entity_id,
                    # fan speed is clamped between 1 and 2
                    # since only NLLF is such a device
                    # and it can only supports fan_speed 1 or 2
                    "fan_speed": max(min(2, speed), 1),
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_fan_speed)


class ShutterMixin(EntityBase):
    """Mixin for shutter data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize shutter mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.current_position: int | None = None
        self.target_position: int | None = None

    async def async_set_target_position(self, target_position: int) -> bool:
        """Set shutter to target position."""

        json_roller_shutter = {
            "modules": [
                {
                    "id": self.entity_id,
                    "target_position": max(min(100, target_position), -1),
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_roller_shutter)

    async def async_open(self) -> bool:
        """Open shutter."""

        return await self.async_set_target_position(100)

    async def async_close(self) -> bool:
        """Close shutter."""

        return await self.async_set_target_position(0)

    async def async_stop(self) -> bool:
        """Stop shutter."""

        return await self.async_set_target_position(-1)


class CameraMixin(EntityBase):
    """Mixin for camera data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize camera mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.sd_status: int | None = None
        self.vpn_url: str | None = None
        self.local_url: str | None = None
        self.is_local: bool | None = None
        self.alim_status: int | None = None
        self.device_type: DeviceType

    async def async_get_live_snapshot(self) -> bytes | None:
        """Fetch live camera image."""

        if not self.local_url and not self.vpn_url:
            return None
        resp = await self.home.auth.async_get_image(
            base_url=f"{self.local_url or self.vpn_url}",
            endpoint="/live/snapshot_720.jpg",
            timeout=10,
        )

        return resp if isinstance(resp, bytes) else None

    async def async_update_camera_urls(self) -> None:
        """Update and validate the camera urls."""

        if self.device_type == "NDB":
            self.is_local = None

        if self.vpn_url and self.is_local:
            temp_local_url = await self._async_check_url(self.vpn_url)
            if temp_local_url:
                try:
                    self.local_url = await self._async_check_url(
                        temp_local_url,
                    )
                except ClientConnectorError as exc:
                    LOG.debug("Cannot connect to %s - reason: %s", temp_local_url, exc)
                    self.is_local = False
                    self.local_url = None

    async def _async_check_url(self, url: str) -> str | None:
        """Validate camera url."""

        try:
            resp = await self.home.auth.async_post_api_request(
                base_url=f"{url}",
                endpoint="/command/ping",
            )

        except ApiError:
            LOG.debug("Api error for camera url %s", url)
            return None

        assert not isinstance(resp, bytes)
        resp_data = await resp.json()
        return resp_data.get("local_url") if resp_data else None


class FloodlightMixin(EntityBase):
    """Mixin for floodlight data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize floodlight mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.floodlight: str | None = None

    async def async_set_floodlight_state(self, state: str) -> bool:
        """Set floodlight state."""

        json_floodlight_state = {
            "modules": [
                {
                    "id": self.entity_id,
                    "floodlight": state,
                },
            ],
        }
        return await self.home.async_set_state(json_floodlight_state)

    async def async_floodlight_on(self) -> bool:
        """Turn on floodlight."""

        return await self.async_set_floodlight_state("on")

    async def async_floodlight_off(self) -> bool:
        """Turn off floodlight."""

        return await self.async_set_floodlight_state("off")

    async def async_floodlight_auto(self) -> bool:
        """Set floodlight to auto mode."""

        return await self.async_set_floodlight_state("auto")


class StatusMixin(EntityBase):
    """Mixin for status data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize status mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.status: str | None = None


class MonitoringMixin(EntityBase):
    """Mixin for monitoring data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize monitoring mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.monitoring: bool | None = None

    async def async_set_monitoring_state(self, state: str) -> bool:
        """Set monitoring state."""

        json_monitoring_state = {
            "modules": [
                {
                    "id": self.entity_id,
                    "monitoring": state,
                },
            ],
        }
        return await self.home.async_set_state(json_monitoring_state)

    async def async_monitoring_on(self) -> bool:
        """Turn on monitoring."""

        return await self.async_set_monitoring_state("on")

    async def async_monitoring_off(self) -> bool:
        """Turn off monitoring."""

        return await self.async_set_monitoring_state("off")


class EnergyHistoryMixin(EntityBase):
    """Mixin for history data."""

    def __init__(self, home: Home, module: ModuleT):
        """Initialize history mixin."""

        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.historical_data: list[dict[str, Any]] | None = None
        self.start_time: int | None = None
        self.end_time: int | None = None
        self.interval: MeasureInterval | None = None
        self.sum_energy_elec: int | None = None
        self.sum_energy_elec_peak: int | None = None
        self.sum_energy_elec_off_peak: int | None = None

    def reset_measures(self):
        self.start_time = None
        self.end_time = None
        self.historical_data = []
        self.sum_energy_elec = 0
        self.sum_energy_elec_peak = 0
        self.sum_energy_elec_off_peak = 0

        
    def _log_energy_error(self, start_time, end_time, msg=None, body=None):
        if body is None:
            body = "NO BODY"
        LOG.debug("!!!!!!!!! ENERGY error %s %s %s %s",
            msg,
                  self.name,
                  datetime.fromtimestamp(start_time),
                  datetime.fromtimestamp(end_time), start_time, end_time, body)

    async def async_update_measures(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        interval: MeasureInterval = MeasureInterval.HOUR,
        days: int = 7,
    ) -> int | None:
        """Update historical data."""

        if end_time is None:
            end_time = int(datetime.now().timestamp())

        if start_time is None:
            end = datetime.fromtimestamp(end_time)
            start_time = end - timedelta(days=days)
            start_time = int(start_time.timestamp())


        prev_start_time = self.start_time
        prev_end_time = self.end_time

        self.start_time = start_time
        self.end_time = end_time

        #the legrand/netatmo handling of start and endtime is very peculiar
        #for 30mn/1h/3h intervals : in fact the starts is asked_start + intervals/2 ! yes so shift of 15mn, 30mn and 1h30
        #for 1day : start is ALWAYS 12am (half day) of the first day of the range
        #for 1week : it will be half week ALWAYS, ie on a thursday at 12am (half day)

        #in fact in the case for all intervals the reported dates are "the middle" of the ranges
        delta_range = MEASURE_INTERVAL_TO_SECONDS.get(interval, 0)//2

        num_calls = 0

        data_points = self.home.energy_endpoints
        raw_datas = []

        LOG.debug("INFO: doing async_update_measures for %s", self.name)

        for data_point in data_points:

            params = {
                "device_id": self.bridge,
                "module_id": self.entity_id,
                "scale": interval.value,
                "type": data_point,
                "date_begin": start_time,
                "date_end": end_time,
            }


            resp = await self.home.auth.async_post_api_request(
                endpoint=GETMEASURE_ENDPOINT,
                params=params,
            )

            rw_dt_f = await resp.json()
            rw_dt = rw_dt_f.get("body")

            if rw_dt is None:
                self._log_energy_error(start_time, end_time, msg=f"direct from {data_point}", body=rw_dt_f)
                raise ApiError(
                    f"Energy badly formed resp: {rw_dt_f} - "
                    f"module: {self.name} - "
                    f"when accessing '{data_point}'"
                )

            num_calls +=1
            raw_datas.append(rw_dt)



        hist_good_vals = []
        energy_schedule_vals = []

        peak_off_peak_mode = False
        if len(raw_datas) > 1 and len(self.home.energy_schedule_vals) > 0:
            peak_off_peak_mode = True

        interval_sec = 2 * delta_range

        if peak_off_peak_mode:
            max_interval_sec = interval_sec
            for cur_energy_peak_or_off_peak_mode, values_lots in enumerate(raw_datas):
                for values_lot in values_lots:
                    try:
                        max_interval_sec = max(max_interval_sec, int(values_lot["step_time"]))
                    except:
                        self._log_energy_error(start_time, end_time,
                                               msg=f"step_time missing {data_points[cur_energy_peak_or_off_peak_mode]}",
                                               body=raw_datas[cur_energy_peak_or_off_peak_mode])
                        # maybe we continue with default step time? or do we have an error?


            biggest_day_interval = (max_interval_sec)//(3600*24) + 1

            energy_schedule_vals = copy.copy(self.home.energy_schedule_vals)

            if energy_schedule_vals[-1][0] < max_interval_sec + (3600*24):
                if energy_schedule_vals[0][1] == energy_schedule_vals[-1][1]:
                    #it means the last one continue in the first one the next day
                    energy_schedule_vals_next = energy_schedule_vals[1:]
                else:
                    energy_schedule_vals_next = copy.copy(self.home.energy_schedule_vals)

                for d in range(0, biggest_day_interval):
                    next_day_extension = [ (offset + ((d+1)*24*3600), mode) for offset,mode in energy_schedule_vals_next]
                    energy_schedule_vals.extend(next_day_extension)



        for cur_energy_peak_or_off_peak_mode, values_lots in enumerate(raw_datas):
            for values_lot in values_lots:
                try:
                    start_lot_time = int(values_lot["beg_time"])
                except:
                    self._log_energy_error(start_time, end_time,
                                           msg=f"beg_time missing {data_points[cur_energy_peak_or_off_peak_mode]}",
                                           body=raw_datas[cur_energy_peak_or_off_peak_mode])
                    raise ApiError(
                        f"Energy badly formed resp beg_time missing: {raw_datas[cur_energy_peak_or_off_peak_mode]} - "
                        f"module: {self.name} - "
                        f"when accessing '{data_points[cur_energy_peak_or_off_peak_mode]}'"
                    )

                try:
                    interval_sec = int(values_lot["step_time"])
                except:
                    self._log_energy_error(start_time, end_time, msg=f"step_time missing {data_points[cur_energy_peak_or_off_peak_mode]}", body=raw_datas[cur_energy_peak_or_off_peak_mode])
                    #maybe we contineu with default step time?

                cur_start_time = start_lot_time
                for val_arr in values_lot.get("value",[]):
                    val = val_arr[0]


                    if peak_off_peak_mode:

                        d_srt = datetime.fromtimestamp(cur_start_time)
                        #offset from start of the day
                        day_origin = int(datetime(d_srt.year, d_srt.month, d_srt.day).timestamp())
                        srt_beg = cur_start_time - day_origin

                        #now check if srt_beg is in a schedule span of the right type
                        idx_start = self._get_proper_in_schedule_index(energy_schedule_vals, srt_beg)

                        if self.home.energy_schedule_vals[idx_start][1] != cur_energy_peak_or_off_peak_mode:

                            #we are NOT in a proper schedule time for this time span ... jump to the next one... meaning it is the next day!
                            if idx_start == len(energy_schedule_vals) - 1:
                                #should never append with the performed day extension above
                                self._log_energy_error(start_time, end_time,
                                                       msg=f"bad idx missing {data_points[cur_energy_peak_or_off_peak_mode]}",
                                                       body=raw_datas[cur_energy_peak_or_off_peak_mode])

                                return 0
                            else:
                                #by construction of the energy schedule the next one should be of opposite mode
                                if energy_schedule_vals[idx_start + 1][1] != cur_energy_peak_or_off_peak_mode:
                                    self._log_energy_error(start_time, end_time,
                                                           msg=f"bad schedule {data_points[cur_energy_peak_or_off_peak_mode]}",
                                                           body=raw_datas[cur_energy_peak_or_off_peak_mode])
                                    return 0



                                start_time_to_get_closer = energy_schedule_vals[idx_start+1][0]
                                diff_t = start_time_to_get_closer - srt_beg
                                cur_start_time = day_origin + srt_beg + (diff_t//interval_sec + 1)*interval_sec

                    hist_good_vals.append((cur_start_time, val, cur_energy_peak_or_off_peak_mode))
                    cur_start_time = cur_start_time + interval_sec


        hist_good_vals = sorted(hist_good_vals, key=itemgetter(0))

        self.historical_data = []

        prev_sum_energy_elec = self.sum_energy_elec
        self.sum_energy_elec = 0
        self.sum_energy_elec_peak = 0
        self.sum_energy_elec_off_peak = 0
        self.end_time = end_time

        computed_start = 0
        computed_end = 0
        for cur_start_time, val, cur_energy_peak_or_off_peak_mode in hist_good_vals:

            self.sum_energy_elec += val

            if peak_off_peak_mode:
                mode = "off_peak"
                if cur_energy_peak_or_off_peak_mode == ENERGY_ELEC_PEAK_IDX:
                    self.sum_energy_elec_peak += val
                    mode = "peak"
                else:
                    self.sum_energy_elec_off_peak += val
            else:
                mode = "standard"

            if computed_start == 0:
                computed_start = cur_start_time - delta_range
            computed_end = cur_start_time + delta_range


            self.historical_data.append(
                {
                    "duration": (2*delta_range)//60,
                    "startTime": f"{datetime.fromtimestamp(cur_start_time - delta_range + 1, tz=timezone.utc).isoformat().split('+')[0]}Z",
                    "endTime": f"{datetime.fromtimestamp(cur_start_time + delta_range, tz=timezone.utc).isoformat().split('+')[0]}Z",
                    "Wh": val,
                    "energyMode": mode,
                    "startTimeUnix": cur_start_time - delta_range,
                    "endTimeUnix": cur_start_time + delta_range

                },
            )

        LOG.debug("=> Success in energy update %s from: %s to %s computed_start: %s, computed_end: %s , sum=%f prev_sum=%f", self.name, datetime.fromtimestamp(start_time), datetime.fromtimestamp(end_time), datetime.fromtimestamp(computed_start), datetime.fromtimestamp(computed_end), self.sum_energy_elec, prev_sum_energy_elec)
        if prev_sum_energy_elec is not None and prev_sum_energy_elec > self.sum_energy_elec:
            LOG.debug(
                ">>>>>>>>>> ENERGY GOING DOWN %s from: %s to %s computed_start: %s, computed_end: %s , sum=%f prev_sum=%f prev_start: %s, prev_end %s",
                self.name, datetime.fromtimestamp(start_time), datetime.fromtimestamp(end_time),
                datetime.fromtimestamp(computed_start), datetime.fromtimestamp(computed_end), self.sum_energy_elec,
                prev_sum_energy_elec, datetime.fromtimestamp(prev_start_time), datetime.fromtimestamp(prev_end_time))

        return num_calls

    def _get_proper_in_schedule_index(self, energy_schedule_vals, srt_beg):
        idx = bisect.bisect_left(energy_schedule_vals, srt_beg, key=itemgetter(0))
        if idx >= len(energy_schedule_vals):
            idx = len(energy_schedule_vals) - 1
        elif energy_schedule_vals[idx][0] > srt_beg:  # if strict equal idx is the good one
            idx = max(0, idx - 1)
        return idx


class Module(NetatmoBase):
    """Class to represent a Netatmo module."""

    device_type: DeviceType
    device_category: DeviceCategory | None
    room_id: str | None

    modules: list[str] | None
    reachable: bool | None
    features: set[str]

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize a Netatmo module instance."""

        super().__init__(module)

        self.device_type = DeviceType(module["type"])

        self.home = home
        self.room_id = module.get("room_id")
        self.reachable = module.get("reachable")
        self.bridge = module.get("bridge")
        self.modules = module.get("modules_bridged")
        self.device_category = DEVICE_CATEGORY_MAP.get(self.device_type)
        self.features = set()

    async def update(self, raw_data: RawData) -> None:
        """Update module with the latest data."""

        self.update_topology(raw_data)
        self.update_features()

        if not self.reachable and self.modules:
            # Update bridged modules and associated rooms
            for module_id in self.modules:
                module = self.home.modules[module_id]
                await module.update(raw_data)
                if module.room_id:
                    self.home.rooms[module.room_id].update(raw_data)

    def update_features(self) -> None:
        """Update features."""

        self.features.update({var for var in vars(self) if var not in ATTRIBUTE_FILTER})
        if "battery_state" in vars(self) or "battery_percent" in vars(self):
            self.features.add("battery")
        if "wind_angle" in self.features:
            self.features.add("wind_direction")
            self.features.add("gust_direction")


# pylint: disable=too-many-ancestors


class Camera(
    FirmwareMixin,
    MonitoringMixin,
    EventMixin,
    CameraMixin,
    WifiMixin,
    Module,
):
    """Class to represent a Netatmo camera."""

    async def update(self, raw_data: RawData) -> None:
        """Update camera with the latest data."""

        await Module.update(self, raw_data)
        await self.async_update_camera_urls()


class Switch(FirmwareMixin, EnergyHistoryMixin, PowerMixin, SwitchMixin, Module):
    """Class to represent a Netatmo switch."""

    ...


class Dimmer(DimmableMixin, Switch):
    """Class to represent a Netatmo dimmer."""

    ...


class Shutter(FirmwareMixin, ShutterMixin, Module):
    """Class to represent a Netatmo shutter."""

    ...


class Fan(FirmwareMixin, FanSpeedMixin, PowerMixin, Module):
    """Class to represent a Netatmo ventilation device."""

    ...


# pylint: enable=too-many-ancestors
