"""Climate platform for Neo Tion breezers."""

from __future__ import annotations

import logging
import asyncio
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TionDataUpdateCoordinator
from .entity import TionEntity

_LOGGER = logging.getLogger(__name__)

FAN_MODES = ["1", "2", "3", "4", "5", "6"]
SWING_INDOOR = "indoor"
SWING_OUTDOOR = "outdoor"
SWING_BOTH = "both"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TionDataUpdateCoordinator = entry.runtime_data
    entities: list[TionBreezerClimate] = []

    for guid, data in coordinator.data.items():
        if data.get("type") == "breezer":
            entities.append(TionBreezerClimate(coordinator, guid, data["name"]))

    async_add_entities(entities)


class TionBreezerClimate(TionEntity, ClimateEntity):
    """Representation of a Tion breezer as a climate entity."""

    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = 10
    _attr_max_temp = 30
    _attr_fan_modes = FAN_MODES
    _attr_swing_modes = [SWING_INDOOR, SWING_OUTDOOR, SWING_BOTH]
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY, HVACMode.AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: TionDataUpdateCoordinator, guid: str, name: str) -> None:
        super().__init__(coordinator, guid, name, "breezer")
        self._attr_unique_id = f"{guid}_climate"
        self._attr_name = None
        self._last_speed: int = 1

    @property
    def native_current_temperature(self) -> float | None:
        return self._device_data.get("current_temperature")

    @property
    def native_target_temperature(self) -> float | None:
        return self._device_data.get("target_temperature")

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._device_data.get("is_on"):
            return HVACMode.OFF
        if self._device_data.get("zone_mode") == "auto":
            return HVACMode.AUTO
        return HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> HVACAction | None:
        if not self._device_data.get("is_on"):
            return HVACAction.OFF
        if self._device_data.get("heater_enabled"):
            return HVACAction.HEATING
        return HVACAction.FAN

    @property
    def fan_mode(self) -> str | None:
        speed = self._device_data.get("speed")
        if speed is None or speed == 0:
            return None
        return str(int(speed))

    @property
    def swing_mode(self) -> str:
        return self._device_data.get("swing_mode", SWING_OUTDOOR)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send_speed(0)
            await self._send_swing("horizontal")
        elif hvac_mode == HVACMode.AUTO:
            await self._send_mode("auto")
            await self._send_swing("horizontal")
        else:
            await self._send_mode("manual")
            await self._send_speed(self._last_speed)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        speed = int(fan_mode)
        if speed > 0:
            self._last_speed = speed
        await self._send_mode("manual")
        await self._send_speed(speed)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        target = swing_mode
        if swing_mode == "indoor":
            target = "vertical"
        elif swing_mode == "outdoor":
            target = "horizontal"
        await self._send_swing(target)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._send_temperature(temp)

    async def async_turn_on(self) -> None:
        await self._send_speed(self._last_speed)

    async def async_turn_off(self) -> None:
        await self._send_speed(0)
        await self._send_swing("horizontal")

    async def _send_mode(self, mode: str) -> None:
        device = self.coordinator.devices.get(self._device_guid)
        if device and getattr(device, "zone", None):
            device.zone.mode = mode
            await self.hass.async_add_executor_job(device.send)
            await asyncio.sleep(1)

    async def _send_speed(self, speed: int) -> None:
        device = self.coordinator.devices.get(self._device_guid)
        if not device:
            return
        if speed == 0:
            device.speed = 0
        elif getattr(device, "zone", None) and device.zone.mode == "auto":
            device.speed_min_set = 0
            device.speed_max_set = speed
            if getattr(device, "speed", 0) == 0:
                device.speed = 1
        else:
            device.speed = speed
        await self.hass.async_add_executor_job(device.send)
        await asyncio.sleep(1)

    async def _send_swing(self, swing: str) -> None:
        device = self.coordinator.devices.get(self._device_guid)
        if device and hasattr(device, "swing"):
            device.swing.mode = swing
            await self.hass.async_add_executor_job(device.send)
            await asyncio.sleep(1)

    async def _send_temperature(self, temp: float) -> None:
        device = self.coordinator.devices.get(self._device_guid)
        if device:
            device.t_set = int(temp)
            device.heater_enabled = True
            if getattr(device, "speed", 0) == 0:
                device.speed = 1
            await self.hass.async_add_executor_job(device.send)
            self.hass.async_create_task(self.coordinator.async_fast_refresh())