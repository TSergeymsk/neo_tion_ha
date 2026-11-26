"""Sensor platform for Neo Tion MagicAir and Breezers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TionDataUpdateCoordinator
from .entity import TionEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TionDataUpdateCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for guid, data in coordinator.data.items():
        name = data.get("name", "Tion Device")
        device_type = data.get("type")

        if device_type == "magicair":
            entities.extend([
                TionSensor(coordinator, guid, name, device_type, "co2", "CO2", CONCENTRATION_PARTS_PER_MILLION, SensorDeviceClass.CO2),
                TionSensor(coordinator, guid, name, device_type, "temperature", "Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "humidity", "Humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY),
            ])
            
        elif device_type == "breezer":
            entities.extend([
                TionSensor(coordinator, guid, name, device_type, "current_temperature", "Temperature In", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "out_temperature", "Temperature Out", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "target_temperature", "Target Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "heater_enabled", "Heater State"),
                TionSensor(coordinator, guid, name, device_type, "speed", "Fan Speed Current"),
                TionSensor(coordinator, guid, name, device_type, "min_speed", "Fan Speed Min"),
                TionSensor(coordinator, guid, name, device_type, "max_speed", "Fan Speed Max"),
                TionSensor(coordinator, guid, name, device_type, "zone_mode", "Mode"),
                TionSensor(coordinator, guid, name, device_type, "target_co2", "Target CO2", CONCENTRATION_PARTS_PER_MILLION, SensorDeviceClass.CO2),
                TionSensor(coordinator, guid, name, device_type, "swing_mode", "Swing Mode"),
            ])

    async_add_entities(entities)


class TionSensor(TionEntity, SensorEntity):
    """Representation of a Tion sensor."""

    def __init__(
        self,
        coordinator: TionDataUpdateCoordinator,
        guid: str,
        device_name: str,
        device_type: str,
        data_key: str,
        name_suffix: str,
        unit: str | None = None,
        device_class: SensorDeviceClass | None = None,
    ) -> None:
        super().__init__(coordinator, guid, device_name, device_type)
        self._data_key = data_key
        self._attr_unique_id = f"{guid}_{data_key}"
        self._attr_name = name_suffix
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        
        if unit:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | int | str | bool | None:
        val = self._device_data.get(self._data_key)
        if isinstance(val, bool):
            return "on" if val else "off"
        if self._data_key in ["speed", "min_speed", "max_speed"] and val is not None:
            return int(val)
        return val

    @property
    def icon(self) -> str | None:
        """Динамические иконки с цифровыми индикаторами скорости (0–6)."""
        if self._data_key == "speed":
            speed = int(self.native_value or 0)
            if 0 <= speed <= 6:
                return f"mdi:numeric-{speed}-circle-outline"
            return "mdi:fan"

        icons = {
            "current_temperature": "mdi:home-thermometer",
            "out_temperature": "mdi:thermometer-lines",
            "target_temperature": "mdi:thermometer-check",
            "temperature": "mdi:thermometer",
            "co2": "mdi:molecule-co2",
            "target_co2": "mdi:molecule-co2",
            "humidity": "mdi:water-percent",
            "heater_enabled": "mdi:radiator",
            "zone_mode": "mdi:auto-fix",
            "swing_mode": "mdi:air-conditioner",
            "min_speed": "mdi:speedometer-slow",
            "max_speed": "mdi:speedometer",
        }
        return icons.get(self._data_key, "mdi:eye")