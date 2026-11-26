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

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
            config_entry=entry,
        )

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
        data: dict[str, Any] = {}

        for device in devices:
            # Определяем тип устройства по имени класса (Breezer или MagicAir)
            cls_name = device.__class__.__name__
            guid = getattr(device, "guid", None) or getattr(device, "device_guid", None)
            if not guid:
                continue

            if cls_name == "Breezer":
                data[guid] = {
                    "type": "breezer",
                    "name": getattr(device, "name", "Tion Breezer"),
                    "is_on": device.is_on,
                    "speed": device.speed,
                    "mode": getattr(device.zone, "mode", "manual") if device.zone else "manual",
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