"""Module to represent a Netatmo room."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any, cast

from pyatmo.const import (
    AWAY,
    COOLING,
    FROSTGUARD,
    HEATING,
    HOME,
    IDLE,
    MANUAL,
    MAX,
    OFF,
    PILOT_WIRE_AWAY,
    PILOT_WIRE_COMFORT,
    PILOT_WIRE_COMFORT_1,
    PILOT_WIRE_COMFORT_2,
    PILOT_WIRE_FROST_GUARD,
    PILOT_WIRE_STAND_BY,
    SCHEDULE,
    SETROOMTHERMPOINT_ENDPOINT,
    UNKNOWN,
    RawData,
)
from pyatmo.enums import TemperatureControlMode
from pyatmo.modules.base_class import NetatmoBase
from pyatmo.modules.device_types import ApplianceType, DeviceCategory, DeviceType
from pyatmo.modules.module import ApplianceTypeMixin, Boiler, PowerMixin

if TYPE_CHECKING:
    from pyatmo.home import Home
    from pyatmo.modules.module import Module

LOG: logging.Logger = logging.getLogger(__name__)

MODE_MAP: dict[str, str] = {SCHEDULE: HOME}

# Climate setpoint mode -> pilot-wire ("fil pilote") preset.
# Many-to-one: several modes collapse onto PILOT_WIRE_COMFORT.
_CLIMATE_SETPOINT_MODE_TO_PILOT_WIRE: dict[str, str] = {
    MANUAL: PILOT_WIRE_COMFORT,
    MAX: PILOT_WIRE_COMFORT,
    OFF: PILOT_WIRE_FROST_GUARD,
    HOME: PILOT_WIRE_COMFORT,  # HOME is equivalent to a schedule for Netatmo NLC based room
    FROSTGUARD: PILOT_WIRE_FROST_GUARD,
    SCHEDULE: PILOT_WIRE_COMFORT,
    AWAY: PILOT_WIRE_AWAY,
}

# Pilot-wire preset -> canonical NLC climate setpoint mode. Not the inverse of
# the map above: it picks one canonical mode per preset and also covers presets
# the forward map never emits (COMFORT_1, COMFORT_2, STAND_BY) that can arrive
# straight from the API.
_PILOT_WIRE_TO_CLIMATE_SETPOINT_MODE: dict[str, str] = {
    PILOT_WIRE_COMFORT: MANUAL,
    PILOT_WIRE_AWAY: MANUAL,  # AWAY is like ECO for a pilot wire heater, so put manual to force it to happen
    PILOT_WIRE_FROST_GUARD: FROSTGUARD,
    PILOT_WIRE_STAND_BY: FROSTGUARD,
    PILOT_WIRE_COMFORT_1: HOME,
    PILOT_WIRE_COMFORT_2: HOME,
}


def climate_setpoint_mode_to_pilot_wire(mode: str) -> str:
    """Map a climate setpoint mode to its pilot-wire preset (frost guard default)."""
    return _CLIMATE_SETPOINT_MODE_TO_PILOT_WIRE.get(mode, PILOT_WIRE_FROST_GUARD)


def pilot_wire_to_climate_setpoint_mode(pilot_wire: str) -> str:
    """Map a pilot-wire preset back to the canonical NLC setpoint mode (frost guard default)."""
    return _PILOT_WIRE_TO_CLIMATE_SETPOINT_MODE.get(pilot_wire, FROSTGUARD)


@dataclass
class Room(NetatmoBase):
    """Class to represent a Netatmo room."""

    modules: dict[str, Module]
    device_types: set[DeviceType]
    features: set[str]

    climate_type: DeviceType | None = None

    air_quality: int | None = None
    algo_schedule_start: int | None = None
    algo_status: int | None = None
    auto_close_ts: int | None = None
    co2: int | None = None
    humidity: int | None = None
    lux: int | None = None
    max_comfort_co2: int | None = None
    max_comfort_humidity: int | None = None
    max_comfort_temperature: int | None = None
    min_comfort_humidity: int | None = None
    min_comfort_temperature: int | None = None
    temperature: int | None = None
    therm_measured_temperature: float | None = None

    reachable: bool | None = None

    heating_power_request: int | None = None
    therm_setpoint_temperature: float | None = None

    therm_setpoint_mode: str | None = None
    therm_setpoint_fp: str | None = None
    support_pilot_wire: bool = False

    therm_setpoint_start_time: int | None = None
    therm_setpoint_end_time: int | None = None

    anticipating: bool | None = None
    open_window: bool | None = None

    cooling_setpoint_temperature: float | None = None
    cooling_setpoint_start_time: int | None = None
    cooling_setpoint_end_time: int | None = None
    cooling_setpoint_mode: str | None = None

    radiators_power: int | None = None

    room_type: str | None = None  # API "type": kitchen, bedroom, livingroom, ...
    therm_relay: str | None = None  # main device id of the controlling heating module

    def __init__(
        self,
        home: Home,
        room: dict[str, Any],
        all_modules: dict[str, Module],
    ) -> None:
        """Initialize a Netatmo room instance."""

        super().__init__(room)
        self.home = home
        self.support_pilot_wire = False
        self.room_type = room.get("type")
        self.therm_relay = room.get("therm_relay")
        self.modules = {
            m_id: m
            for m_id, m in all_modules.items()
            if m_id in room.get("module_ids", [])
        }
        self.device_types = set()
        self.features = set()
        self.evaluate_device_type()

    def update_topology(self, raw_data: RawData) -> None:
        """Update room topology."""

        self.name = raw_data.get("name", UNKNOWN)
        self.room_type = raw_data.get("type", self.room_type)
        self.therm_relay = raw_data.get("therm_relay", self.therm_relay)
        self.modules = {
            m_id: m
            for m_id, m in self.home.modules.items()
            if m_id in raw_data.get("module_ids", [])
        }
        self.evaluate_device_type()

    def evaluate_device_type(self) -> None:
        """Evaluate the device type of the room."""

        self.support_pilot_wire = False
        for module in self.modules.values():
            self.device_types.add(module.device_type)
            if module.device_category is not None:
                self.features.add(module.device_category.name)
            if (
                module.device_type == "NLC"
                and isinstance(module, ApplianceTypeMixin)
                and module.appliance_type == ApplianceType.radiator
            ):
                self.support_pilot_wire = True
                # Regarding to the room the cable outlet can be seen as climate control, add the climate feature
                self.features.add(DeviceCategory.climate.name)

        if "OTM" in self.device_types:
            self.climate_type = DeviceType.OTM
        elif "NATherm1" in self.device_types:
            self.climate_type = DeviceType.NATherm1
        elif "BNS" in self.device_types:
            self.climate_type = DeviceType.BNS
            self.features.add("humidity")
        elif "NRV" in self.device_types:
            self.climate_type = DeviceType.NRV
        elif "NAC" in self.device_types:
            self.climate_type = DeviceType.NAC
        elif "BNTH" in self.device_types:
            self.climate_type = DeviceType.BNTH
        elif "NLC" in self.device_types and self.support_pilot_wire:
            self.climate_type = DeviceType.NLC

    def update(self, raw_data: RawData) -> None:
        """Update room data."""

        self.air_quality = raw_data.get("air_quality")
        self.algo_schedule_start = raw_data.get("algo_schedule_start")
        self.algo_status = raw_data.get("algo_status")
        self.auto_close_ts = raw_data.get("auto_close_ts")
        self.co2 = raw_data.get("co2")
        self.humidity = raw_data.get("humidity")
        self.lux = raw_data.get("lux")
        self.max_comfort_co2 = raw_data.get("max_comfort_co2")
        self.max_comfort_humidity = raw_data.get("max_comfort_humidity")
        self.max_comfort_temperature = raw_data.get("max_comfort_temperature")
        self.min_comfort_humidity = raw_data.get("min_comfort_humidity")
        self.min_comfort_temperature = raw_data.get("min_comfort_temperature")
        self.temperature = raw_data.get("temperature")
        self.radiators_power = 0

        if self.climate_type == DeviceType.BNTH:
            # BNTH is wired, so the room is always reachable
            self.reachable = True
        elif self.climate_type == DeviceType.NLC:
            self.reachable = raw_data.get("reachable", False)
            for module in self.modules.values():
                if (
                    isinstance(module, ApplianceTypeMixin)
                    and module.device_type == DeviceType.NLC
                    and module.appliance_type == ApplianceType.radiator
                ):
                    if isinstance(module, PowerMixin) and module.power is not None:
                        self.radiators_power += module.power

                    if hasattr(module, "reachable"):
                        state = module.reachable
                        if state is not None:
                            if self.reachable is None:
                                self.reachable = state
                            else:
                                self.reachable = (
                                    self.reachable or state
                                )  # as soon as we do have one
        else:
            self.reachable = raw_data.get("reachable")

        self.therm_measured_temperature = raw_data.get("therm_measured_temperature")

        self.heating_power_request = raw_data.get("heating_power_request")
        self.therm_setpoint_mode = raw_data.get("therm_setpoint_mode")
        self.therm_setpoint_fp = raw_data.get("therm_setpoint_fp")
        self.therm_setpoint_temperature = raw_data.get("therm_setpoint_temperature")
        self.therm_setpoint_start_time = raw_data.get("therm_setpoint_start_time")
        self.therm_setpoint_end_time = raw_data.get("therm_setpoint_end_time")

        self.anticipating = raw_data.get("anticipating")
        self.open_window = raw_data.get("open_window")

        self.cooling_setpoint_temperature = raw_data.get("cooling_setpoint_temperature")
        self.cooling_setpoint_start_time = raw_data.get("cooling_setpoint_start_time")
        self.cooling_setpoint_end_time = raw_data.get("cooling_setpoint_end_time")
        self.cooling_setpoint_mode = raw_data.get("cooling_setpoint_mode")

    async def async_therm_manual(
        self,
        temp: float | None = None,
        end_time: int | None = None,
    ) -> None:
        """Set room temperature set point to manual."""

        await self.async_therm_set(MANUAL, temp, end_time)

    async def async_therm_home(self, end_time: int | None = None) -> None:
        """Set room temperature set point to home."""

        await self.async_therm_set(HOME, end_time=end_time)

    async def async_therm_frostguard(self, end_time: int | None = None) -> None:
        """Set room temperature set point to frostguard."""

        await self.async_therm_set(FROSTGUARD, end_time=end_time)

    async def async_therm_set(
        self,
        mode: str | None = None,
        temp: float | None = None,
        end_time: int | None = None,
        pilot_wire: str | None = None,
    ) -> None:
        """Set room temperature set point."""

        if mode is None:
            mode = MANUAL

        mode = MODE_MAP.get(mode, mode)

        if "NATherm1" in self.device_types or (
            "NRV" in self.device_types
            and not self.home.has_otm()
            and not self.home.has_bns()
        ):
            await self._async_set_thermpoint(mode, temp, end_time)

        else:
            await self._async_therm_set(mode, temp, end_time, pilot_wire)

    async def _async_therm_set(
        self,
        mode: str | None = None,
        temp: float | None = None,
        end_time: int | None = None,
        pilot_wire: str | None = None,
    ) -> bool:
        """Set room temperature set point (OTM)."""
        if pilot_wire is None:
            # in case both are None stop everything
            if mode is None:
                mode = FROSTGUARD
            pilot_wire = climate_setpoint_mode_to_pilot_wire(mode)
            # force back the proper preset mode in case of pilot wire
            # to comply with netatmo model
            if self.support_pilot_wire and self.climate_type == DeviceType.NLC:
                mode = pilot_wire_to_climate_setpoint_mode(pilot_wire)

        if pilot_wire is not None and mode is None:
            mode = MANUAL

        temp_mode_mapping: dict[TemperatureControlMode | None, str] = {
            None: "therm",
            TemperatureControlMode.HEATING: "therm",
            TemperatureControlMode.COOLING: "cooling",
        }

        setpoint_mode_prefix: str = temp_mode_mapping.get(
            self.home.temperature_control_mode,
            "therm",
        )

        room_payload: dict[str, Any] = {
            "id": self.entity_id,
            f"{setpoint_mode_prefix}_setpoint_mode": mode,
        }

        if temp:
            room_payload[f"{setpoint_mode_prefix}_setpoint_temperature"] = temp

        if end_time:
            room_payload[f"{setpoint_mode_prefix}_setpoint_end_time"] = end_time

        if self.support_pilot_wire and pilot_wire:
            room_payload["therm_setpoint_fp"] = pilot_wire

        json_therm_set: dict[str, Any] = {"rooms": [room_payload]}

        return await self.home.async_set_state(json_therm_set)

    async def _async_set_thermpoint(
        self,
        mode: str,
        temp: float | None = None,
        end_time: int | None = None,
    ) -> None:
        """Set room temperature set point (NRV, NATherm1)."""

        post_params: dict[str, str] = {
            "home_id": self.home.entity_id,
            "room_id": self.entity_id,
            "mode": mode,
        }
        # Temp and endtime should only be sent when mode=='manual', but netatmo api can
        # handle that even when mode == 'home' and these settings don't make sense
        if temp is not None:
            post_params["temp"] = str(temp)

        if end_time is not None:
            post_params["endtime"] = str(end_time)

        LOG.debug(
            "Setting room (%s) temperature set point to %s until %s",
            self.entity_id,
            temp,
            end_time,
        )
        await self.home.auth.async_post_api_request(
            endpoint=SETROOMTHERMPOINT_ENDPOINT,
            params=post_params,
        )

    @property
    def boiler_status(self) -> bool | None:
        """Return the boiler status."""

        for module in self.modules.values():
            if hasattr(module, "boiler_status"):
                module = cast("Boiler", module)
                if (boiler_status := module.boiler_status) is not None:
                    return boiler_status

        return None

    @property
    def setpoint_mode(self) -> str:
        """Return the current setpoint mode."""

        return self.therm_setpoint_mode or self.cooling_setpoint_mode or UNKNOWN

    @property
    def setpoint_temperature(self) -> float | None:
        """Return the current setpoint temperature."""

        return (
            self.therm_setpoint_temperature or self.cooling_setpoint_temperature or None
        )

    @property
    def setpoint_fp(self) -> str | None:
        """Return the current setpoint 'Fil pilote (FP)'."""

        return self.therm_setpoint_fp or None

    @property
    def hvac_action(self) -> str:
        """Return the current HVAC action."""

        if self.setpoint_mode == OFF:
            return OFF

        if self.boiler_status is True:
            return HEATING

        if self.heating_power_request is not None and self.heating_power_request > 0:
            return HEATING

        if self.cooling_setpoint_temperature:
            return COOLING

        return IDLE
