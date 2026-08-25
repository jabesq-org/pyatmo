"""Module to represent a Netatmo module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
import logging
from operator import itemgetter
from time import time
from typing import TYPE_CHECKING, Any, cast

from aiohttp import ClientConnectorError, ClientResponse

from pyatmo.const import (
    GETMEASURE_ENDPOINT,
    SETSTATE_ENDPOINT,
    WEBRTC_OFFER_ENDPOINT,
    WEBRTC_TERMINATE_ENDPOINT,
    RawData,
)
from pyatmo.exceptions import ApiError
from pyatmo.modules.base_class import (
    EntityBase,
    NetatmoBase,
    Place,
    bridged_module_ids,
    update_name,
)
from pyatmo.modules.device_types import (
    DEVICE_CATEGORY_MAP,
    ApplianceType,
    BoilerControl,
    BoilerError,
    DeviceCategory,
    DeviceType,
    DhwControl,
    DoorTagCategory,
)
from pyatmo.webrtc import WebRTCAnswer, WebRTCStream

if TYPE_CHECKING:
    from pyatmo.event import Event
    from pyatmo.home import Home


LOG = logging.getLogger(__name__)


ModuleT = dict[str, Any]

# Multi-gang devices get one /homestatus entry per gang, keyed `<parent id>#<n>`.
# Four things depend on this convention -- `Module.is_sub_module`,
# `Module.parent_module_id`, the presence rule in `Module.update`, and the skip in
# `propagate_reachability` -- and they must agree, so it lives here.
SUB_MODULE_SEPARATOR = "#"

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
    "history_features",
    "history_features_values",
    "appliance_type",
    "doortag_category",
    "last_seen",
    "setup_date",
    "boiler_control",
    "boiler_error",
    "dhw_control",
    "error_code",
    "_reachable",
    "rf_state",
}


def propagate_reachability(
    module: Module,
    value: bool | None,
    seen: set[str] | None = None,
) -> None:
    """Write `value` onto `module` and its bridged children.

    Shared by `Module.mark_unreachable` and `Module.clear_unreachable` so the two
    walks cannot drift apart: whatever the mark reaches, the clear reaches too.

    Sub-modules are skipped. A `#`-suffixed id resolves its reachability from its
    parent on read and its own payload never carries the key, so a value written
    here would never be lifted again.

    `seen` guards the walk. `modules_bridged` is unvalidated API data and a cycle in
    it would otherwise recurse until the stack runs out.
    """
    seen = set() if seen is None else seen
    if module.entity_id in seen:
        return
    seen.add(module.entity_id)

    module._reachable = value  # noqa: SLF001
    for module_id in module.modules or []:
        if SUB_MODULE_SEPARATOR in module_id:
            continue
        if (child := module.home.modules.get(module_id)) is not None:
            propagate_reachability(child, value, seen)


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
    return mapping.get(data, 0)


class FirmwareMixin(EntityBase):
    """Mixin for firmware data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize firmware mixin."""
        super().__init__(home, module)
        self.firmware_revision: int | None = None
        self.firmware_name: str | None = None


class WifiMixin(EntityBase):
    """Mixin for wifi data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize wifi mixin."""
        super().__init__(home, module)
        self.wifi_strength: int | None = None


class RfMixin(EntityBase):
    """Mixin for rf data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize rf mixin."""

        super().__init__(home, module)
        self.rf_state: str | None = None
        self.rf_strength: int | None = None


class RainMixin(EntityBase):
    """Mixin for rain data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize rain mixin."""

        super().__init__(home, module)
        self.rain: float | None = None
        self.sum_rain_1: float | None = None
        self.sum_rain_24: float | None = None


class WindMixin(EntityBase):
    """Mixin for wind data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize wind mixin."""

        super().__init__(home, module)
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
    angle_mapping = {
        (0, 30): "N",
        (30, 60): "NE",
        (60, 120): "E",
        (120, 150): "SE",
        (150, 210): "S",
        (210, 240): "SW",
        (240, 300): "W",
        (300, 330): "NW",
        (330, 360): "N",
    }
    for (lower, upper), direction in angle_mapping.items():
        if lower <= angle < upper:
            return direction
    return "N"  # Default case


class TemperatureMixin(EntityBase):
    """Mixin for temperature data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize temperature mixin."""

        super().__init__(home, module)
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

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize humidity mixin."""

        super().__init__(home, module)
        self.humidity: int | None = None


class CO2Mixin(EntityBase):
    """Mixin for CO2 data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize CO2 mixin."""

        super().__init__(home, module)
        self.co2: int | None = None


class HealthIndexMixin(EntityBase):
    """Mixin for health index data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize health index mixin."""

        super().__init__(home, module)
        self.health_idx: int | None = None


class NoiseMixin(EntityBase):
    """Mixin for noise data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize noise mixin."""

        super().__init__(home, module)
        self.noise: int | None = None


class PressureMixin(EntityBase):
    """Mixin for pressure data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize pressure mixin."""

        super().__init__(home, module)
        self.pressure: float | None = None
        self.absolute_pressure: float | None = None
        self.pressure_trend: str | None = None


class BoilerMixin(EntityBase):
    """Mixin for boiler data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize boiler mixin."""

        super().__init__(home, module)
        self.boiler_status: bool | None = None
        self.boiler_valve_comfort_boost: bool | None = None


class OpenThermMixin(EntityBase):
    """Mixin for OpenTherm boiler diagnostics (OTH)."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize OpenTherm mixin."""

        super().__init__(home, module)
        self.boiler_control: BoilerControl | None = None
        self.boiler_error: BoilerError | None = None
        self.dhw_control: DhwControl | None = None


class CoolerMixin(EntityBase):
    """Mixin for cooler data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize cooler mixin."""

        super().__init__(home, module)
        self.cooler_status: bool | None = None


class BatteryMixin(EntityBase):
    """Mixin for battery data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize battery mixin."""

        super().__init__(home, module)
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

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize place mixin."""

        super().__init__(home, module)
        self.place: Place | None = None


class DimmableMixin(EntityBase):
    """Mixin for dimmable data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize dimmable mixin."""

        super().__init__(home, module)
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

    device_category: DeviceCategory | None
    appliance_type: ApplianceType | None

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize appliance type mixin."""

        super().__init__(home, module)
        self.appliance_type: ApplianceType | None = module.get(
            "appliance_type",
            ApplianceType.unknown,
        )


class DoorTagCategoryMixin(EntityBase):
    """Mixin for category data."""

    doortag_category: DoorTagCategory | None

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize category mixin."""

        super().__init__(home, module)
        self.doortag_category: DoorTagCategory | None = module.get(
            "category",
            DoorTagCategory.unknown,
        )


class PowerMixin(EntityBase):
    """Mixin for power data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize power mixin."""

        super().__init__(home, module)
        self.power: int | None = None
        self.history_features.add("power")


class EventMixin(EntityBase):
    """Mixin for event data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize event mixin."""

        super().__init__(home, module)
        self.events: list[Event] = []


class ContactorMixin(EntityBase):
    """Mixin for contactor data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize contactor mixin."""

        super().__init__(home, module)
        self.contactor_mode: str | None = None


class OffloadMixin(EntityBase):
    """Mixin for offload data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize offload mixin."""

        super().__init__(home, module)
        self.offload: bool | None = None
        self.offload_meters: list[str] | None = None


class SwitchMixin(EntityBase):
    """Mixin for switch data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize switch mixin."""

        super().__init__(home, module)
        self.on: bool | None = None

    async def async_set_switch(self, target_position: bool) -> bool:
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

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize fan speed mixin."""

        super().__init__(home, module)
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
    """Mixin for shutter data.

    The capability properties below all default to True. That is a fallback,
    not a positive assertion: the API describes no shutter type's abilities,
    so every module is assumed capable unless it says otherwise, which keeps
    each type behaving as it always has. A type known to lack one of them
    should override it rather than have it inferred.
    """

    __open_position = 100
    __close_position = 0
    __stop_position = -1
    __preferred_position = -2

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize shutter mixin."""

        super().__init__(home, module)
        # when can_report_position is False, this is not a real position - it
        # mirrors the last commanded target, and 101 means never instructed,
        # so it can fall outside the normal 0-100 range
        self.current_position: int | None = None
        self.target_position: int | None = None
        self.target_position__step: int | None = None

    async def async_set_target_position(self, target_position: int) -> bool:
        """Set shutter to target position."""

        # in case of a too low value, we default to stop and not the preferred position
        # We check against __preferred_position that is the lower known value
        if target_position < self.__preferred_position:
            target_position = self.__stop_position

        json_roller_shutter = {
            "modules": [
                {
                    "id": self.entity_id,
                    "target_position": min(self.__open_position, target_position),
                    "bridge": self.bridge,
                },
            ],
        }
        return await self.home.async_set_state(json_roller_shutter)

    async def async_open(self) -> bool:
        """Open shutter."""

        return await self.async_set_target_position(self.__open_position)

    async def async_close(self) -> bool:
        """Close shutter."""

        return await self.async_set_target_position(self.__close_position)

    async def async_stop(self) -> bool:
        """Stop shutter."""

        return await self.async_set_target_position(self.__stop_position)

    async def async_move_to_preferred_position(self) -> bool:
        """Move shutter to preferred position."""

        return await self.async_set_target_position(self.__preferred_position)

    @property
    def can_set_target_position(self) -> bool:
        """Return whether the actor accepts an arbitrary target position.

        False for actors that only support open/close/stop, where sending a
        percentage is either rejected or silently coerced by the hardware.
        """

        return True

    @property
    def can_report_position(self) -> bool:
        """Return whether `current_position` reflects the actor's real position.

        False for actors that only echo the last commanded target instead of
        reporting an actual, physically measured position.
        """

        return True

    @property
    def can_move_to_preferred_position(self) -> bool:
        """Return whether the actor accepts `async_move_to_preferred_position`.

        False for actors that reject the preset command outright, even though
        they otherwise support open/close/stop and exact positioning.
        """

        return True


class CameraMixinBase(EntityBase):
    """Base class for camera mixins."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize camera mixin."""

        super().__init__(home, module)
        self.sd_status: int | None = None
        self.vpn_url: str | None = None
        self.local_url: str | None = None
        self.is_local: bool | None = None
        self.alim_status: int | None = None
        self.device_type: DeviceType

        self._force_vpn_url = False

    @property
    def camera_url(self) -> str | None:
        """Return the camera URL, if available.

        Depending on the camera streaming protocol, this URL can be used to retrieve:
          - The live snapshot (HLS and WebRTC).
          - The live stream (HLS only).
        """
        return self.local_url or self.vpn_url

    async def async_get_live_snapshot(self) -> bytes | None:
        """Fetch live camera image."""

        url = self.camera_url

        if not url:
            return None

        resp = await self.home.auth.async_get_image(
            base_url=f"{url}",
            endpoint="/live/snapshot_720.jpg",
        )

        return resp if isinstance(resp, bytes) else None

    async def async_update_camera_urls(self) -> None:
        """Update and validate the camera urls."""

        if self._force_vpn_url:
            self.local_url = None
            return

        if self.vpn_url and self.is_local:
            temp_local_url = await self._async_check_url(self.vpn_url)
            if temp_local_url:
                try:
                    self.local_url = await self._async_check_url(
                        temp_local_url,
                    )
                except (TimeoutError, ClientConnectorError) as exc:
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

        if isinstance(resp, bytes):
            msg = "Invalid response from camera url"
            raise ApiError(msg)

        resp_data = await resp.json()
        return resp_data.get("local_url") if resp_data else None


class HLSCameraMixin(CameraMixinBase):
    """Mixin for cameras using the HLS protocol."""


class WebRTCCameraMixin(CameraMixinBase):
    """Mixin for cameras using the WebRTC protocol."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize WebRTC camera mixin."""

        super().__init__(home, module)

        # WebRTC cameras don't support accessing the live stream nor snapshot via the local URL
        self._force_vpn_url = True

    async def async_start_stream(self, session_id: str, sdp_offer: str) -> WebRTCAnswer:
        """Start WebRTC streaming session.

        Netatmo cameras do not support ICE trickle when accessed through third-party applications,
        so the SDP offer must include all ICE candidates.
        """

        params = {
            "home_id": self.home.entity_id,
            "device_id": self.entity_id,
            "sdp": sdp_offer,
            "session_id": session_id,
        }

        resp = await self.home.auth.async_post_api_request(
            endpoint=WEBRTC_OFFER_ENDPOINT, params=params
        )

        json_resp = await resp.json()
        resp_body = self._parse_webrtc_response_body(json_resp)

        try:
            if session_id != resp_body["session_id"]:
                msg = "Invalid WebRTC answer: session ID mismatch"
                raise ApiError(msg)

            tag_id = resp_body["tag_id"]
            sdp_answer = resp_body["sdpAnswer"]
        except KeyError as exc:
            msg = f"Invalid WebRTC answer: missing {exc} field"
            raise ApiError(msg) from exc

        return WebRTCAnswer(WebRTCStream(session_id, tag_id), sdp_answer)

    async def async_stop_stream(self, stream: WebRTCStream) -> None:
        """Stop an active WebRTC streaming session."""

        params = {
            "home_id": self.home.entity_id,
            "device_id": self.entity_id,
            "session_id": stream.session_id,
            "tag_id": stream.tag_id,
        }

        resp = await self.home.auth.async_post_api_request(
            endpoint=WEBRTC_TERMINATE_ENDPOINT, params=params
        )

        json_resp = await resp.json()
        self._parse_webrtc_response_body(json_resp)

    def _parse_webrtc_response_body(self, json_resp: dict[str, Any]) -> dict[str, Any]:
        """Extract the body from a WebRTC API response and check for errors."""

        if not json_resp:
            msg = "Empty WebRTC response"
            raise ApiError(msg)

        try:
            resp_body = json_resp["body"]

            if resp_body["status"] != "ok":
                error_dict = resp_body["error"]
                error_code = error_dict["code"]
                error_msg = error_dict["message"]

                msg = f"WebRTC API error: {error_msg} ({error_code})"
                raise ApiError(msg)
        except KeyError as exc:
            msg = f"Invalid WebRTC response: missing {exc} field"
            raise ApiError(msg) from exc

        return resp_body


class FloodlightMixin(EntityBase):
    """Mixin for floodlight data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize floodlight mixin."""

        super().__init__(home, module)
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


class SirenMixin(EntityBase):
    """Mixin for siren data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize siren mixin."""

        super().__init__(home, module)
        self.siren_status: str | None = None

    async def async_set_siren_state(
        self, state: str, base_url: str | None = None
    ) -> bool:
        """Set siren state.

        Uses the public OAuth2 API by default. Pass base_url=SIREN_BASE_URL
        to route via app.netatmo.net, which currently accepts siren_status
        where the public API rejects it (error code 21).
        """

        resp = await self.home.auth.async_post_api_request(
            endpoint=SETSTATE_ENDPOINT,
            base_url=base_url,
            params={
                "json": {
                    "home": {
                        "id": self.home.entity_id,
                        "modules": [
                            {
                                "id": self.entity_id,
                                "siren_status": state,
                            },
                        ],
                    },
                },
            },
        )
        return (await resp.json()).get("status") == "ok"

    async def async_siren_on(self, base_url: str | None = None) -> bool:
        """Turn on siren."""

        return await self.async_set_siren_state("sound", base_url=base_url)

    async def async_siren_off(self, base_url: str | None = None) -> bool:
        """Turn off siren."""

        return await self.async_set_siren_state("no_sound", base_url=base_url)


class StatusMixin(EntityBase):
    """Mixin for status data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize status mixin."""

        super().__init__(home, module)
        self.status: str | None = None


class MonitoringMixin(EntityBase):
    """Mixin for monitoring data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize monitoring mixin."""

        super().__init__(home, module)
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
    """Measure interval."""

    HALF_HOUR = "30min"
    HOUR = "1hour"
    THREE_HOURS = "3hours"
    DAY = "1day"
    WEEK = "1week"
    MONTH = "1month"


class MeasureType(Enum):
    """Measure type."""

    BOILERON = "boileron"
    BOILEROFF = "boileroff"
    SUM_BOILER_ON = "sum_boiler_on"
    SUM_BOILER_OFF = "sum_boiler_off"
    SUM_ENERGY_ELEC = "sum_energy_buy_from_grid"
    SUM_ENERGY_ELEC_BASIC = "sum_energy_buy_from_grid$0"
    SUM_ENERGY_ELEC_PEAK = "sum_energy_buy_from_grid$1"
    SUM_ENERGY_ELEC_OFF_PEAK = "sum_energy_buy_from_grid$2"
    SUM_ENERGY_PRICE = "sum_energy_buy_from_grid_price"
    SUM_ENERGY_PRICE_BASIC = "sum_energy_buy_from_grid_price$0"
    SUM_ENERGY_PRICE_PEAK = "sum_energy_buy_from_grid_price$1"
    SUM_ENERGY_PRICE_OFF_PEAK = "sum_energy_buy_from_grid_price$2"
    SUM_ENERGY_ELEC_LEGACY = "sum_energy_elec"
    SUM_ENERGY_ELEC_BASIC_LEGACY = "sum_energy_elec$0"
    SUM_ENERGY_ELEC_PEAK_LEGACY = "sum_energy_elec$1"
    SUM_ENERGY_ELEC_OFF_PEAK_LEGACY = "sum_energy_elec$2"


MEASURE_INTERVAL_TO_SECONDS = {
    MeasureInterval.HALF_HOUR: 1800,
    MeasureInterval.HOUR: 3600,
    MeasureInterval.THREE_HOURS: 10800,
    MeasureInterval.DAY: 86400,
    MeasureInterval.WEEK: 604800,
    MeasureInterval.MONTH: 2592000,
}

ENERGY_FILTERS: str = (
    f"{MeasureType.SUM_ENERGY_ELEC.value},"
    f"{MeasureType.SUM_ENERGY_ELEC_BASIC.value},"
    f"{MeasureType.SUM_ENERGY_ELEC_PEAK.value},"
    f"{MeasureType.SUM_ENERGY_ELEC_OFF_PEAK.value}"
)
ENERGY_FILTERS_LEGACY: str = (
    f"{MeasureType.SUM_ENERGY_ELEC_LEGACY.value},"
    f"{MeasureType.SUM_ENERGY_ELEC_BASIC_LEGACY.value},"
    f"{MeasureType.SUM_ENERGY_ELEC_PEAK_LEGACY.value},"
    f"{MeasureType.SUM_ENERGY_ELEC_OFF_PEAK_LEGACY.value}"
)
ENERGY_FILTERS_MODES: list[str] = ["generic", "basic", "peak", "off_peak"]


def compute_riemann_sum(
    power_data: list[tuple[int, float]],
    conservative: bool = False,
) -> float:
    """Compute energy from power with a rieman sum."""

    delta_energy = 0.0
    if power_data and len(power_data) > 1:
        # compute a rieman sum, as best as possible , trapezoidal, taking pessimistic asumption
        # as we don't want to artifically go up the previous one
        # (except in rare exceptions like reset, 0 , etc)

        for i in range(len(power_data) - 1):
            dt_h = float(power_data[i + 1][0] - power_data[i][0]) / 3600.0

            if conservative:
                d_p_w = 0.0
            else:
                d_p_w = abs(float(power_data[i + 1][1] - power_data[i][1]))

            d_nrj_wh = dt_h * (
                min(power_data[i + 1][1], power_data[i][1]) + 0.5 * d_p_w
            )

            delta_energy += d_nrj_wh

    return delta_energy


class EnergyHistoryMixin(EntityBase):
    """Mixin for Energy history data."""

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize history mixin."""

        super().__init__(home, module)
        self.historical_data: list[dict[str, Any]] | None = None
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.interval: MeasureInterval | None = None
        self.sum_energy_elec: float = 0.0
        self.sum_energy_elec_peak: float = 0.0
        self.sum_energy_elec_off_peak: float = 0.0
        self._anchor_for_power_adjustment: float | None = None
        self.in_reset: bool = False

    def reset_measures(
        self,
        start_power_time: datetime | None,
        in_reset: bool = True,
    ) -> None:
        """Reset energy measures."""

        self.in_reset = in_reset
        self.historical_data = []
        self.sum_energy_elec = 0.0
        self.sum_energy_elec_peak = 0.0
        self.sum_energy_elec_off_peak = 0.0
        if start_power_time is None:
            self._anchor_for_power_adjustment = start_power_time
        else:
            self._anchor_for_power_adjustment = int(start_power_time.timestamp())

    def get_sum_energy_elec_power_adapted(
        self,
        to_ts: float | None = None,
        conservative: bool = False,
    ) -> tuple[float, float]:
        """Compute proper energy value with adaptation from power."""

        v = self.sum_energy_elec

        delta_energy = 0.0

        if not self.in_reset:
            if to_ts is None:
                to_ts = int(time())

            from_ts = self._anchor_for_power_adjustment

            if (
                from_ts is not None
                and from_ts < to_ts
                and isinstance(self, PowerMixin)
                and isinstance(self, NetatmoBase)
            ):
                power_data = self.get_history_data(
                    "power",
                    from_ts=from_ts,
                    to_ts=to_ts,
                )
                if isinstance(
                    self,
                    EnergyHistoryMixin,
                ):  # well to please the linter....
                    delta_energy = compute_riemann_sum(power_data, conservative)

        return v, delta_energy

    def _log_energy_error(
        self,
        start_time: float,
        end_time: float,
        msg: str | None = None,
        body: dict | None = None,
    ) -> None:
        LOG.debug(
            "ENERGY collection error %s %s %s %s %s %s %s",
            msg,
            self.name,
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time),
            start_time,
            end_time,
            body or "NO BODY",
        )

    async def async_update_measures(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        interval: MeasureInterval = MeasureInterval.HOUR,
        days: int = 7,
    ) -> None:
        """Update historical data."""

        if end_time is None:
            end_time = int(datetime.now().timestamp())

        if start_time is None:
            end = datetime.fromtimestamp(end_time)
            start_time = int((end - timedelta(days=days)).timestamp())

        prev_start_time = self.start_time
        prev_end_time = self.end_time

        self.start_time = start_time
        self.end_time = end_time

        # the legrand/netatmo handling of start and endtime is very peculiar
        # for 30mn/1h/3h intervals : in fact the starts is asked_start + intervals/2 !
        # => so shift of 15mn, 30mn and 1h30
        # for 1day : start is ALWAYS 12am (half day) of the first day of the range
        # for 1week : it will be half week ALWAYS, ie on a thursday at 12am (half day)
        # in fact in the case for all intervals the reported dates are "the middle" of the ranges

        delta_range = MEASURE_INTERVAL_TO_SECONDS.get(interval, 0) // 2

        _, raw_data = await self._energy_api_calls(start_time, end_time, interval)

        hist_good_vals = await self._get_aligned_energy_values_and_mode(
            start_time,
            end_time,
            delta_range,
            raw_data,
        )

        prev_sum_energy_elec = self.sum_energy_elec
        self.sum_energy_elec = 0.0
        self.sum_energy_elec_peak = 0.0
        self.sum_energy_elec_off_peak = 0.0

        # no data at all: we know nothing for the end: best guess, it is the start
        self._anchor_for_power_adjustment = start_time

        self.in_reset = False

        if len(hist_good_vals) == 0:
            # nothing has been updated or changed it can nearly be seen as an error, but the api is answering correctly
            # so we probably have to reset to 0 anyway as it means there were no exisitng
            # historical data for this time range

            LOG.debug(
                "NO VALUES energy update %s from: %s to %s,  prev_sum=%s",
                self.name,
                datetime.fromtimestamp(start_time),
                datetime.fromtimestamp(end_time),
                prev_sum_energy_elec if prev_sum_energy_elec is not None else "NOTHING",
            )
        else:
            await self._prepare_exported_historical_data(
                start_time,
                end_time,
                delta_range,
                hist_good_vals,
                prev_end_time or 0.0,
                prev_start_time or 0.0,
                prev_sum_energy_elec or 0.0,
            )

    async def _prepare_exported_historical_data(
        self,
        start_time: float,
        end_time: float,
        delta_range: float,
        hist_good_vals: list[tuple[int, float, list[float]]],
        prev_end_time: float,
        prev_start_time: float,
        prev_sum_energy_elec: float | None,
    ) -> None:
        self.historical_data = []
        computed_start = 0.0
        computed_end = 0.0
        computed_end_for_calculus = 0.0
        for cur_start_time, val, vals in hist_good_vals:
            self.sum_energy_elec += val

            modes = []
            val_modes = []

            for i, v in enumerate(vals):
                if v is not None:
                    modes.append(ENERGY_FILTERS_MODES[i])
                    val_modes.append(v)
                    if ENERGY_FILTERS_MODES[i] == "off_peak":
                        self.sum_energy_elec_off_peak += v
                    elif ENERGY_FILTERS_MODES[i] == "peak":
                        self.sum_energy_elec_peak += v

            c_start = cur_start_time
            c_end = cur_start_time + 2 * delta_range

            if computed_start == 0:
                computed_start = c_start
            computed_end = c_end

            computed_end_for_calculus = c_end

            start_time_string = f"{datetime.fromtimestamp(c_start + 1, tz=UTC).isoformat().split('+')[0]}Z"
            end_time_string = (
                f"{datetime.fromtimestamp(c_end, tz=UTC).isoformat().split('+')[0]}Z"
            )
            self.historical_data.append(
                {
                    "duration": (2 * delta_range) // 60,
                    "startTime": start_time_string,
                    "endTime": end_time_string,
                    "Wh": val,
                    "energyMode": modes,
                    "WhPerModes": val_modes,
                    "startTimeUnix": c_start,
                    "endTimeUnix": c_end,
                },
            )
        if (
            prev_sum_energy_elec is not None
            and prev_sum_energy_elec > self.sum_energy_elec
        ):
            msg = (
                "ENERGY GOING DOWN %s from: %s to %s "
                "computed_start: %s, computed_end: %s, "
                "sum=%f prev_sum=%f prev_start: %s, prev_end %s"
            )
            LOG.debug(
                msg,
                self.name,
                datetime.fromtimestamp(start_time),
                datetime.fromtimestamp(end_time),
                datetime.fromtimestamp(computed_start),
                datetime.fromtimestamp(computed_end),
                self.sum_energy_elec,
                prev_sum_energy_elec,
                datetime.fromtimestamp(prev_start_time),
                datetime.fromtimestamp(prev_end_time),
            )
        else:
            msg = (
                "Success in energy update %s from: %s to %s "
                "computed_start: %s, computed_end: %s , sum=%s prev_sum=%s"
            )
            LOG.debug(
                msg,
                self.name,
                datetime.fromtimestamp(start_time),
                datetime.fromtimestamp(end_time),
                datetime.fromtimestamp(computed_start),
                datetime.fromtimestamp(computed_end),
                self.sum_energy_elec,
                prev_sum_energy_elec if prev_sum_energy_elec is not None else "NOTHING",
            )

        self._anchor_for_power_adjustment = computed_end_for_calculus

    async def _get_aligned_energy_values_and_mode(
        self,
        start_time: float,
        end_time: float,
        delta_range: float,
        raw_data: dict,
    ) -> list[Any]:
        hist_good_vals = []
        values_lots = raw_data

        for values_lot in values_lots:
            try:
                start_lot_time = int(values_lot["beg_time"])
            except KeyError:
                self._log_energy_error(
                    start_time,
                    end_time,
                    msg="beg_time missing",
                    body=values_lots,
                )
                msg = (
                    f"Energy badly formed resp beg_time missing: {values_lots} - "
                    f"module: {self.name}"
                )
                raise ApiError(
                    msg,
                ) from None

            interval_sec = values_lot.get("step_time")
            if interval_sec is None:
                if len(values_lot.get("value", [])) > 1:
                    self._log_energy_error(
                        start_time,
                        end_time,
                        msg="step_time missing",
                        body=values_lots,
                    )
                interval_sec = 2 * delta_range
            else:
                interval_sec = int(interval_sec)

            # align the start on the begining of the segment
            cur_start_time = start_lot_time - interval_sec // 2
            for val_arr in values_lot.get("value", []):
                vals: list[int | None] = []
                val = 0
                for v in val_arr:
                    if v is not None:
                        v = int(v)
                        val += v
                        vals.append(v)
                    else:
                        vals.append(None)

                hist_good_vals.append((cur_start_time, val, vals))
                cur_start_time = cur_start_time + interval_sec

        return sorted(hist_good_vals, key=itemgetter(0))

    def _get_energy_filers(self) -> str:
        return ENERGY_FILTERS

    async def _energy_api_calls(
        self,
        start_time: float,
        end_time: float,
        interval: MeasureInterval,
    ) -> tuple[str, Any]:
        filters: str = self._get_energy_filers()

        params = {
            "device_id": self.bridge,
            "module_id": self.entity_id,
            "scale": interval.value,
            "type": filters,
            "date_begin": start_time,
            "date_end": end_time,
        }

        resp: ClientResponse = await self.home.auth.async_post_api_request(
            endpoint=GETMEASURE_ENDPOINT,
            params=params,
        )

        rw_dt_f = await resp.json()
        rw_dt = rw_dt_f.get("body")

        if rw_dt is None:
            self._log_energy_error(
                start_time,
                end_time,
                msg=f"direct from {filters}",
                body=rw_dt_f,
            )
            msg: str = (
                f"Energy badly formed resp: {rw_dt_f} - "
                f"module: {self.name} - "
                f"when accessing '{filters}'"
            )
            raise ApiError(msg)

        raw_data = rw_dt

        return filters, raw_data


class EnergyHistoryLegacyMixin(EnergyHistoryMixin):
    """Mixin for Energy history data, Using legacy APis (used for NLE)."""

    def _get_energy_filers(self) -> str:
        return ENERGY_FILTERS_LEGACY


class Module(NetatmoBase):
    """Class to represent a Netatmo module."""

    device_type: DeviceType
    device_category: DeviceCategory | None
    room_id: str | None

    modules: list[str] | None
    _reachable: bool | None
    last_seen: int | None
    setup_date: int | None
    error_code: int | None
    features: set[str]

    def __init__(self, home: Home, module: ModuleT) -> None:
        """Initialize a Netatmo module instance."""

        super().__init__(module)

        self.device_type = DeviceType(module["type"])

        self.home = home
        self.room_id = module.get("room_id")
        self._reachable = module.get("reachable")
        self.last_seen = module.get("last_seen")
        self.setup_date = module.get("setup_date")
        self.error_code = None
        self.bridge = module.get("bridge")
        self.modules = bridged_module_ids(module)
        self.device_category = DEVICE_CATEGORY_MAP.get(self.device_type)
        self.features = set()

    @property
    def is_sub_module(self) -> bool:
        """Whether this is a `#`-suffixed sub-entry of a parent module.

        Multi-gang devices such as the Legrand NLIS and the NLY 3-phase meter get
        one `/homestatus` entry per gang, keyed `<parent id>#<n>`. Those entries
        carry almost nothing -- notably never `reachable`.
        """
        return SUB_MODULE_SEPARATOR in self.entity_id

    @property
    def parent_module_id(self) -> str | None:
        """The id this sub-module hangs off, or None if it is not a sub-module.

        Note this is the *id* parent, which is not always the `bridge`: an NLIS
        gang's bridge is the gateway, while its parent is the switch it belongs to.
        """
        if not self.is_sub_module:
            return None
        return self.entity_id.split(SUB_MODULE_SEPARATOR, 1)[0]

    @property
    def reachable(self) -> bool | None:
        """Return reachability, falling back to the parent for sub-modules.

        The API reports `reachable` only on the parent entry of a multi-gang
        module such as the Legrand NLIS, so a `#`-suffixed sub-module resolves
        it from the parent. Resolving on read keeps this independent of the
        order modules appear in the /homestatus payload.
        """
        if self._reachable is not None or not self.is_sub_module:
            return self._reachable
        parent = self.home.modules.get(cast("str", self.parent_module_id))
        return parent.reachable if parent else None

    def mark_unreachable(self, seen: set[str] | None = None) -> None:
        """Mark this module and its bridged children unreachable.

        Sub-modules are skipped on purpose: a `#`-suffixed id resolves its
        reachability from the parent module on read, and its own payload never
        reports the key, so stamping it here would pin it unreachable for the
        lifetime of the process.

        `seen` guards the walk. `modules_bridged` is unvalidated API data, and a
        cycle in it would otherwise recurse until the stack runs out.
        """
        propagate_reachability(self, False, seen)

    def mark_reachable(self, seen: set[str] | None = None) -> None:
        """Mark this module and its children reachable, e.g. from a reconnect webhook."""
        propagate_reachability(self, True, seen)

    def clear_unreachable(self, seen: set[str] | None = None) -> None:
        """Drop the mark `mark_unreachable()` left, on this module and its children.

        Reachability becomes unknown rather than reachable: the next payload decides.
        A bridged child that never appears in `/homestatus` has no payload of its own,
        so without this it would hold the `False` it inherited from a single outage of
        its bridge for the lifetime of the process.

        Mirrors `mark_unreachable()` exactly, because both go through
        `propagate_reachability`: whatever the mark reached, the clear reaches too.
        """
        propagate_reachability(self, None, seen)

    async def update(self, raw_data: RawData) -> None:
        """Update module with the latest data."""

        self.update_topology(raw_data)

        if (
            self.bridge
            and self.bridge in self.home.modules
            and hasattr(self, "device_category")
            and self.device_category == "weather"
        ):
            self.name = update_name(self.name, self.home.modules[self.bridge].name)

        self.update_features()

        # Some modules are only ever signalled by their presence: the API lists them in
        # /homestatus but never sends `reachable` for them (weather stations, relays,
        # cameras, the Legrand ecometer). Presence is then the only signal there is, so
        # treat it as reachable. Keyed on the shape of the entry, not on device type.
        #
        # `#`-suffixed sub-modules are excluded: `mark_unreachable()` skips them by
        # design, so a value written here could never be cleared and they would hold a
        # stale True through an outage. Leaving them unset lets `reachable` resolve them
        # from their parent, which follows the outage correctly.
        #
        # `raw_data` must be non-empty: the errors[] path calls `update({})`, which must
        # not resurrect a module `mark_unreachable()` just marked.
        if raw_data and "reachable" not in raw_data and not self.is_sub_module:
            self._reachable = True

    def update_features(self) -> None:
        """Update features."""

        self.features.update({var for var in vars(self) if var not in ATTRIBUTE_FILTER})
        # Every module carries `_reachable`, so this feature is universal — unlike
        # `battery` below. Consumers gate entity creation on the public name.
        self.features.add("reachable")
        if "battery_state" in vars(self) or "battery_percent" in vars(self):
            self.features.add("battery")
        if "wind_angle" in self.features:
            self.features.add("wind_direction")
            self.features.add("gust_direction")


class Camera(
    FirmwareMixin,
    MonitoringMixin,
    EventMixin,
    CameraMixinBase,
    WifiMixin,
    Module,
):
    """Class to represent a Netatmo camera."""

    async def update(self, raw_data: RawData) -> None:
        """Update camera with the latest data."""

        await Module.update(self, raw_data)
        await self.async_update_camera_urls()


class Switch(
    FirmwareMixin,
    EnergyHistoryMixin,
    PowerMixin,
    SwitchMixin,
    ApplianceTypeMixin,
    Module,
):
    """Class to represent a Netatmo switch."""


class Dimmer(DimmableMixin, Switch):
    """Class to represent a Netatmo dimmer."""


class Shutter(FirmwareMixin, ShutterMixin, Module):
    """Class to represent a Netatmo shutter."""


class Fan(FirmwareMixin, FanSpeedMixin, PowerMixin, Module):
    """Class to represent a Netatmo ventilation device."""


class RemoteControlMixin(FirmwareMixin, Module):
    """Class to represent a Netatmo remote control."""


class Energy(EnergyHistoryMixin, Module):
    """Class to represent a Netatmo energy module."""


class Boiler(BoilerMixin, Module):
    """Class to represent a Netatmo boiler."""
