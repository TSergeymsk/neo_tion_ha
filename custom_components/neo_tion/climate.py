"""Climate platform for Neo Tion breezers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TionDataUpdateCoordinator
from .entity import TionEntity

_LOGGER = logging.getLogger(__name__)

FAN_MODES = ["1", "2", "3", "4", "5", "6"]

# В библиотеке tion 1.28 is_on вычисляется из speed:
# speed == 0 -> выключен, speed > 0 -> включён.
# Поэтому управляем именно скоростью.


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tion climate entities."""
    coordinator: TionDataUpdateCoordinator = entry.runtime_data
    entities: list[TionBreezerClimate] = []

    for guid, data in coordinator.data.items():
        if data.get("type") == "breezer":
            entities.append(
                TionBreezerClimate(coordinator, guid, data["name"])
            )

    async_add_entities(entities)


class TionBreezerClimate(TionEntity, ClimateEntity):
    """Representation of a Tion breezer as a climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = 10
    _attr_max_temp = 30
    _attr_fan_modes = FAN_MODES
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        coordinator: TionDataUpdateCoordinator,
        guid: str,
        name: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, guid, name, "breezer")
        self._attr_unique_id = f"{guid}_climate"
        # Запоминаем последнюю ненулевую скорость, чтобы вернуть её при включении
        self._last_speed: int = 1

    @property
    def current_temperature(self) -> float | None:
        return self._device_data.get("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        return self._device_data.get("target_temperature")

    @property
    def hvac_mode(self) -> HVACMode:
        speed = self._device_data.get("speed")
        if speed is not None and speed > 0:
            return HVACMode.FAN_ONLY
        return HVACMode.OFF

    @property
    def fan_mode(self) -> str | None:
        speed = self._device_data.get("speed")
        if speed is None or speed == 0:
            return None
        return str(speed)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self._send_command("set_speed", 0)
        else:
            # При включении восстанавливаем последнюю ненулевую скорость
            await self._send_command("set_speed", self._last_speed)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        speed = int(fan_mode)
        if speed > 0:
            self._last_speed = speed
        await self._send_command("set_speed", speed)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._send_command("set_temperature", temp)

    async def async_turn_on(self) -> None:
        """Turn the breezer on."""
        await self._send_command("set_speed", self._last_speed)

    async def async_turn_off(self) -> None:
        """Turn the breezer off."""
        await self._send_command("set_speed", 0)

    async def _send_command(self, command: str, value: Any) -> None:
        """Send a command to the device via the executor."""
        await self.hass.async_add_executor_job(
            self._send_command_sync, command, value
        )
        await self.coordinator.async_request_refresh()

    def _send_command_sync(self, command: str, value: Any) -> None:
        """Execute command against the cached device object."""
        device = self.coordinator.devices.get(self._device_guid)
        if device is None:
            raise ValueError(
                f"Breezer {self._device_guid} not found in cached devices"
            )

        if command == "set_speed":
            device.speed = int(value)
        elif command == "set_temperature":
            device.heater_temp = int(value)
        else:
            raise ValueError(f"Unknown command: {command}")

        device.send()