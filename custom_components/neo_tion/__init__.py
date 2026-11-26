"""The Neo Tion integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import PLATFORMS
from .coordinator import TionDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# ВАЖНО: без пробела в имени! Совместимо с Python 3.11+
NeoTionConfigEntry = ConfigEntry[TionDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: NeoTionConfigEntry
) -> bool:
    """Set up Neo Tion from a config entry."""
    coordinator = TionDataUpdateCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Tion cloud: {err}"
        ) from err

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: NeoTionConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)