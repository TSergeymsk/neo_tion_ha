"""Data update coordinator for Neo Tion."""

from __future__ import annotations

import logging
import asyncio
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


def create_tion_api(email: str, password: str) -> TionApi:
    try:
        return TionApi(email, password, auth_fname=None)
    except TypeError:
        try:
            return TionApi(email, password, save_auth=False)
        except TypeError:
            return TionApi(email, password)


class TionDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from the Tion cloud API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._email: str = entry.data[CONF_EMAIL]
        self._password: str = entry.data[CONF_PASSWORD]
        self._api: TionApi | None = None
        self._devices: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
            config_entry=entry,
        )

    @property
    def devices(self) -> dict[str, Any]:
        return self._devices

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.hass.async_add_executor_job(self._fetch_data_sync, False)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Tion API: {err}") from err

    def _fetch_data_sync(self, force: bool = False) -> dict[str, Any]:
        if self._api is None:
            self._api = create_tion_api(self._email, self._password)

        if force:
            if hasattr(self._api, "_last_update"):
                self._api._last_update = 0

        devices = self._api.get_devices()
        self._devices = {}
        
        for device in devices:
            guid = getattr(device, "guid", None) or getattr(device, "device_guid", None)
            if guid:
                self._devices[guid] = device
                
                # Возвращен отладочный вывод
                if device.__class__.__name__ == "Breezer":
                    _LOGGER.debug("=== DEBUG BREEZER [%s] ===", getattr(device, "name", "Unknown"))
                    _LOGGER.debug("vars(device): %s", vars(device))

        data: dict[str, Any] = {}
        for guid, device in self._devices.items():
            cls_name = device.__class__.__name__

            if cls_name == "Breezer":
                in_temp = getattr(device, "_t_in", None)
                out_temp = getattr(device, "_t_out", None)
                heater_temp = getattr(device, "t_set", None)
                heater_enabled = getattr(device, "heater_enabled", False)

                speed = int(getattr(device, "speed", 0))
                min_speed = int(getattr(device, "speed_min_set", 0))
                max_speed = int(getattr(device, "speed_max_set", getattr(device, "_speed_limit", 6)))
                
                zone = getattr(device, "zone", None)
                swing = getattr(device, "swing", None)
                
                swing_val = str(getattr(swing, "mode", "horizontal")).lower() if swing else "horizontal"
                if swing_val in ("vertical", "indoor"):
                    swing_val = "indoor"
                elif swing_val in ("horizontal", "outdoor"):
                    swing_val = "outdoor"
                elif swing_val == "off":
                    swing_val = "indoor"

                data[guid] = {
                    "type": "breezer",
                    "name": getattr(device, "name", "Tion Breezer"),
                    "is_on": getattr(device, "is_on", False),
                    "speed": speed,
                    "zone_mode": getattr(zone, "mode", "manual") if zone else "manual",
                    "target_co2": getattr(zone, "target_co2", None) if zone else None,
                    "min_speed": min_speed,
                    "max_speed": max_speed,
                    "heater_enabled": heater_enabled,
                    "target_temperature": heater_temp,
                    "current_temperature": in_temp,
                    "out_temperature": out_temp,
                    "swing_mode": swing_val,
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

    async def async_fast_refresh(self) -> None:
        await asyncio.sleep(5)
        try:
            data = await self.hass.async_add_executor_job(self._fetch_data_sync, True)
            self.async_set_updated_data(data)
        except Exception as err:
            _LOGGER.error("Force refresh failed: %s", err)