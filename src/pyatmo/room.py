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

# as for now all the below is not exposed at all through the API, don't put it in the public API, so not in const.py
NETAMO_CLIMATE_SETPOINT_MODE_TO_PILOT_WIRE: dict[str, str] = {
    MANUAL: PILOT_WIRE_COMFORT,
    MAX: PILOT_WIRE_COMFORT,
    OFF: PILOT_WIRE_FROST_GUARD,
    HOME: PILOT_WIRE_COMFORT,  # HOME is equivalent to a schedule for Netatmo NLC based room
    FROSTGUARD: PILOT_WIRE_FROST_GUARD,
    SCHEDULE: PILOT_WIRE_COMFORT,
    AWAY: PILOT_WIRE_AWAY,
}
# invert of the map above:
NETAMO_PILOT_WIRE_TO_CLIMATE_SETPOINT_MODE: dict[str, str] = {
    PILOT_WIRE_COMFORT: MANUAL,
    PILOT_WIRE_AWAY: MANUAL,  # AWAY is like ECO for a pilot wire heater, so put manual to force it to happen
    PILOT_WIRE_FROST_GUARD: FROSTGUARD,
    PILOT_WIRE_STAND_BY: FROSTGUARD,
    PILOT_WIRE_COMFORT_1: HOME,
    PILOT_WIRE_COMFORT_2: HOME,
}


@dataclass
class Room(NetatmoBase):
    """Class to represent a Netatmo room."""

    modules: dict[str, Module]
    device_types: set[DeviceType]
    features: set[str]

    climate_type: DeviceType | None = None

    humidity: int | None = None
    therm_measured_temperature: float | None = None

    reachable: bool | None = None

    heating_power_request: int | None = None
    therm_setpoint_temperature: float | None = None

    therm_setpoint_mode: str | None = None
    # therm_setpoint_mode: per the documentation: "The thermostat mode in which the room is.
    # For a room controlled by a BNS, mode can be home, manual, max or hg/off (if heating/cooling).
    # For a room controlled by a NLC, mode can be off, manual or hg."
    # values can be
    # "manual"
    # "max"
    # "off"
    # "home"
    # "hg"
    # "schedule"
    # "away"

    # therm_setpoint_fp: used to set up pilot wire, ie "fil pilote" set point
    # netatmo documentation:
    # Usually used to control (Fil pilote (FP)) setpoint
    # values:
    # "comfort"
    # "away"
    # "frost_guard"
    # "stand_by"
    # "comfort_1" => documentation unclear and contradictory here, as it is in the json schema but no in the doc
    # "comfort_2" => same
    # but here:
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

        self.humidity = raw_data.get("humidity")
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
            pilot_wire = NETAMO_CLIMATE_SETPOINT_MODE_TO_PILOT_WIRE.get(
                mode,
                PILOT_WIRE_FROST_GUARD,
            )
            # force back the proper preset mode in case of pilot wire
            # to comply with netatmo model
            if self.support_pilot_wire and self.climate_type == DeviceType.NLC:
                mode = NETAMO_PILOT_WIRE_TO_CLIMATE_SETPOINT_MODE.get(
                    pilot_wire,
                    FROSTGUARD,
                )

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

        json_therm_set: dict[str, Any] = {
            "rooms": [
                {
                    "id": self.entity_id,
                    f"{setpoint_mode_prefix}_setpoint_mode": mode,
                },
            ],
        }

        if temp:
            json_therm_set["rooms"][0][
                f"{setpoint_mode_prefix}_setpoint_temperature"
            ] = temp

        if end_time:
            json_therm_set["rooms"][0][f"{setpoint_mode_prefix}_setpoint_end_time"] = (
                end_time
            )

        if self.support_pilot_wire and pilot_wire:
            json_therm_set["rooms"][0]["therm_setpoint_fp"] = pilot_wire

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
