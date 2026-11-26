"""Base entity for Neo Tion."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TionDataUpdateCoordinator


class TionEntity(CoordinatorEntity[TionDataUpdateCoordinator]):
    """Base class for all Tion entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TionDataUpdateCoordinator,
        device_guid: str,
        device_name: str,
        device_type: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_guid = device_guid
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_guid)},
            name=device_name,
            manufacturer="Tion",
            model=device_type.capitalize(),
        )

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return (
            super().available
            and self._device_guid in self.coordinator.data
        )

    @property
    def _device_data(self) -> dict:
        """Return the data for this device."""
        return self.coordinator.data.get(self._device_guid, {})