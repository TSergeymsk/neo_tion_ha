"""Data update coordinator for Neo Tion."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from tion import TionApi  # type: ignore

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class TionDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from the Tion cloud API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._email = entry.data[CONF_EMAIL]
        self._password = entry.data[CONF_PASSWORD]
        self._api: TionApi | None = None
        # Кэш объектов устройств: guid -> device
        self._devices: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
            config_entry=entry,
        )

    @property
    def api(self) -> TionApi:
        """Return the initialized Tion API client."""
        if self._api is None:
            raise RuntimeError("Tion API not initialized yet")
        return self._api

    @property
    def devices(self) -> dict[str, Any]:
        """Return cached device objects keyed by guid."""
        return self._devices

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Tion API in the executor (library is sync)."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_data_sync)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Tion API: {err}") from err

    def _fetch_data_sync(self) -> dict[str, Any]:
        """Synchronous data fetch, run in the executor."""
        if self._api is None:
            self._api = TionApi(self._email, self._password, save_auth=False)

        devices = self._api.get_devices()

        # Пересобираем кэш объектов устройств
        self._devices = {}
        for device in devices:
            guid = getattr(device, "guid", None) or getattr(
                device, "device_guid", None
            )
            if guid:
                self._devices[guid] = device

        data: dict[str, Any] = {}
        for guid, device in self._devices.items():
            cls_name = device.__class__.__name__

            if cls_name == "Breezer":
                data[guid] = {
                    "type": "breezer",
                    "name": getattr(device, "name", "Tion Breezer"),
                    "is_on": device.is_on,
                    "speed": device.speed,
                    "mode": (
                        getattr(device.zone, "mode", "manual")
                        if device.zone
                        else "manual"
                    ),
                    "current_temperature": getattr(device, "in_temp", None),
                    "target_temperature": getattr(device, "heater_temp", None),
                }
            elif cls_name == "MagicAir":
                data[guid] = {
                    "type": "magicair",
                    "name": getattr(device, "name", "Tion MagicAir"),
                    "co2": getattr(device, "co2", None),
                    "temperature": getattr(device, "temperature", None),
                    "humidity": getattr(device, "humidity", None),
                }
        return data