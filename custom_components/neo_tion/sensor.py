"""Sensor platform for Neo Tion MagicAir and breezer diagnostics."""

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
    """Set up Tion sensors."""
    coordinator: TionDataUpdateCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for guid, data in coordinator.data.items():
        if data.get("type") == "magicair":
            name = data["name"]
            entities.extend(
                [
                    TionSensor(
                        coordinator, guid, name, "co2", "CO2",
                        CONCENTRATION_PARTS_PER_MILLION,
                        SensorDeviceClass.CO2,
                    ),
                    TionSensor(
                        coordinator, guid, name, "temperature", "Temperature",
                        UnitOfTemperature.CELSIUS,
                        SensorDeviceClass.TEMPERATURE,
                    ),
                    TionSensor(
                        coordinator, guid, name, "humidity", "Humidity",
                        PERCENTAGE,
                        SensorDeviceClass.HUMIDITY,
                    ),
                ]
            )
    async_add_entities(entities)


class TionSensor(TionEntity, SensorEntity):
    """Representation of a Tion sensor."""

    def __init__(
        self,
        coordinator: TionDataUpdateCoordinator,
        guid: str,
        device_name: str,
        data_key: str,
        name_suffix: str,
        unit: str,
        device_class: SensorDeviceClass | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, guid, device_name, "magicair")
        self._data_key = data_key
        self._attr_unique_id = f"{guid}_{data_key}"
        self._attr_name = name_suffix
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        return self._device_data.get(self._data_key)