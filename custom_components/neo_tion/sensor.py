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
                # Климат
                TionSensor(coordinator, guid, name, device_type, "current_temperature", "Temperature In", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "out_temperature", "Temperature Out", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "target_temperature", "Target Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
                TionSensor(coordinator, guid, name, device_type, "heater_enabled", "Heater State"),
                
                # Скорости
                TionSensor(coordinator, guid, name, device_type, "speed", "Fan Speed Current"),
                TionSensor(coordinator, guid, name, device_type, "min_speed", "Fan Speed Min"),
                TionSensor(coordinator, guid, name, device_type, "max_speed", "Fan Speed Max"),
                
                # Авто-режим и CO2
                TionSensor(coordinator, guid, name, device_type, "zone_mode", "Mode"),
                TionSensor(coordinator, guid, name, device_type, "target_co2", "Target CO2", CONCENTRATION_PARTS_PER_MILLION, SensorDeviceClass.CO2),
                
                # Жалюзи
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
        """Initialize the sensor."""
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
        return val