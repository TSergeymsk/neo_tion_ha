"""The Neo Tion integration."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity_platform

from .const import PLATFORMS, DOMAIN
from .coordinator import TionDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

NeoTionConfigEntry = ConfigEntry[TionDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: NeoTionConfigEntry) -> bool:
    """Set up Neo Tion from a config entry."""
    coordinator = TionDataUpdateCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        raise ConfigEntryNotReady(f"Unable to connect to Tion cloud: {err}") from err

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NeoTionConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register custom services (Actions)."""
    
    async def handle_set_auto_mode(call: ServiceCall) -> None:
        """Handle the set_auto_mode action."""
        entity_ids = call.data["entity_id"]
        target_co2 = call.data.get("target_co2")
        min_speed = call.data.get("min_speed")
        max_speed = call.data.get("max_speed")
        
        # Находим все climate сущности Tion
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator: TionDataUpdateCoordinator = entry.runtime_data
            for entity in hass.data.get("entity_components", {}).get("climate", []):
                if entity.entity_id in entity_ids and hasattr(entity, "_device_guid"):
                    guid = entity._device_guid
                    device = coordinator.devices.get(guid)
                    if device and getattr(device, "zone", None):
                        if target_co2 is not None:
                            device.zone.target_co2 = target_co2
                        if min_speed is not None:
                            device.zone.min_speed = min_speed
                        if max_speed is not None:
                            device.zone.max_speed = max_speed
                        await hass.async_add_executor_job(device.send)
                        await coordinator.async_fast_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_auto_mode",
        handle_set_auto_mode,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_ids,
            vol.Optional("target_co2"): vol.All(vol.Coerce(int), vol.Range(min=400, max=2000)),
            vol.Optional("min_speed"): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
            vol.Optional("max_speed"): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
        }),
    )

    async def handle_set_heater(call: ServiceCall) -> None:
        """Handle the set_heater action."""
        entity_ids = call.data["entity_id"]
        heater_enabled = call.data["heater_enabled"]
        target_temp = call.data.get("target_temperature")

        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator: TionDataUpdateCoordinator = entry.runtime_data
            for entity in hass.data.get("entity_components", {}).get("climate", []):
                if entity.entity_id in entity_ids and hasattr(entity, "_device_guid"):
                    guid = entity._device_guid
                    device = coordinator.devices.get(guid)
                    if device:
                        device.heater_enabled = heater_enabled
                        if target_temp is not None:
                            device.heater_temp = target_temp
                        await hass.async_add_executor_job(device.send)
                        await coordinator.async_fast_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_heater",
        handle_set_heater,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_ids,
            vol.Required("heater_enabled"): cv.boolean,
            vol.Optional("target_temperature"): vol.All(vol.Coerce(int), vol.Range(min=10, max=30)),
        }),
    )

    return True