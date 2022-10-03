"""Module to represent a Netatmo module."""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict

from pyatmo.const import GETMEASURE_ENDPOINT, RawData
from pyatmo.exceptions import ApiError
from pyatmo.modules.base_class import EntityBase, NetatmoBase, Place
from pyatmo.modules.device_types import DEVICE_CATEGORY_MAP, DeviceCategory, DeviceType

if TYPE_CHECKING:
    from pyatmo.event import Event
    from pyatmo.home import Home

LOG = logging.getLogger(__name__)

ModuleT = Dict[str, Any]

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
        "very low": 10,
    }
    return mapping[data]


class FirmwareMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.firmware_revision: int | None = None
        self.firmware_name: str | None = None


class WifiMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.wifi_strength: int | None = None


class RfMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.rf_strength: int | None = None


class RainMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.rain: float | None = None
        self.sum_rain_1: float | None = None
        self.sum_rain_24: float | None = None


class WindMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
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
    def __init__(self, home: Home, module: ModuleT):
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
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.humidity: int | None = None


class CO2Mixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.co2: int | None = None


class HealthIndexMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.health_idx: int | None = None


class NoiseMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.noise: int | None = None


class PressureMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.pressure: float | None = None
        self.absolute_pressure: float | None = None
        self.pressure_trend: str | None = None


class BoilerMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.boiler_status: bool | None = None


class BatteryMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.battery_state: str | None = None
        self.battery_level: int | None = None
        self.battery_percent: int | None = None

    @property
    def battery(self) -> int:
        if self.battery_percent is not None:
            return self.battery_percent
        if self.battery_state is None:
            return 0
        return process_battery_state(self.battery_state)


class PlaceMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.place: Place | None = None


class DimmableMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
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
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.appliance_type: str | None = None


class EnergyMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.sum_energy_elec: int | None = None


class PowerMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.power: int | None = None


class EventMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.events: list[Event] = []


class SwitchMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
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


class ShutterMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
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
    def __init__(self, home: Home, module: ModuleT):
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
                self.local_url = await self._async_check_url(
                    temp_local_url,
                )

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
    def __init__(self, home: Home, module: ModuleT):
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
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.status: str | None = None


class MonitoringMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
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


class MeasureInterval(Enum):
    HALF_HOUR = "30min"
    HOUR = "1hour"
    THREE_HOURS = "3hours"
    DAY = "1day"
    WEEK = "1week"
    MONTH = "1month"


class MeasureType(Enum):
    BOILERON = "boileron"
    BOILEROFF = "boileroff"
    SUM_BOILER_ON = "sum_boiler_on"
    SUM_BOILER_OFF = "sum_boiler_off"
    SUM_ENERGY_ELEC = "sum_energy_elec"
    SUM_ENERGY_ELEC_BASIC = "sum_energy_elec$0"
    SUM_ENERGY_ELEC_PEAK = "sum_energy_elec$1"
    SUM_ENERGY_ELEC_OFF_PEAK = "sum_energy_elec$2"
    SUM_ENERGY_PRICE = "sum_energy_price"
    SUM_ENERGY_PRICE_BASIC = "sum_energy_price$0"
    SUM_ENERGY_PRICE_PEAK = "sum_energy_price$1"
    SUM_ENERGY_PRICE_OFF_PEAK = "sum_energy_price$2"


class HistoryMixin(EntityBase):
    def __init__(self, home: Home, module: ModuleT):
        super().__init__(home, module)  # type: ignore # mypy issue 4335
        self.historical_data: list[dict[str, Any]] | None = None
        self.start_time: int | None = None
        self.interval: MeasureInterval | None = None

    async def async_update_measures(
        self,
        start_time: int | None = None,
        interval: MeasureInterval = MeasureInterval.HOUR,
        days: int = 7,
    ) -> None:
        end_time = int(datetime.now().timestamp())
        if start_time is None:
            start_time = end_time - days * 24 * 60 * 60

        data_point = MeasureType.SUM_ENERGY_ELEC_BASIC.name
        params = {
            "device_id": self.bridge,
            "module_id": self.entity_id,
            "scale": interval.name,
            "type": data_point,
            "date_begin": start_time,
            "date_end": end_time,
        }

        resp = await self.home.auth.async_post_api_request(
            endpoint=GETMEASURE_ENDPOINT,
            params=params,
        )
        raw_data = await resp.json()

        data = raw_data["body"][0]
        self.start_time = int(data["beg_time"])
        interval_sec = int(data["step_time"])
        interval_min = interval_sec // 60

        self.historical_data = []
        start_time = self.start_time
        for value in data["value"]:
            end_time = start_time + interval_sec
            self.historical_data.append(
                {
                    "duration": interval_min,
                    "startTime": datetime.utcfromtimestamp(start_time + 1).isoformat()
                    + "Z",
                    "endTime": f"{datetime.utcfromtimestamp(end_time).isoformat()}Z",
                    "Wh": value[0],
                },
            )

            start_time = end_time


class Module(NetatmoBase):
    """Class to represent a Netatmo module."""

    device_type: DeviceType
    device_category: DeviceCategory | None
    room_id: str | None

    modules: list[str] | None
    reachable: bool | None
    features: set[str]

    def __init__(self, home: Home, module: ModuleT) -> None:
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
    async def update(self, raw_data: RawData) -> None:
        await Module.update(self, raw_data)
        await self.async_update_camera_urls()


class Switch(FirmwareMixin, PowerMixin, SwitchMixin, Module):
    ...


class Dimmer(DimmableMixin, Switch):
    ...


class Shutter(FirmwareMixin, ShutterMixin, Module):
    ...


# pylint: enable=too-many-ancestors
