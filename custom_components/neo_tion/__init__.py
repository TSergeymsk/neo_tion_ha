"""The Neo Tion integration."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import PLATFORMS, DOMAIN
from .coordinator import TionDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

NeoTionConfigEntry = ConfigEntry[TionDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: NeoTionConfigEntry) -> bool:
    coordinator = TionDataUpdateCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        raise ConfigEntryNotReady(f"Unable to connect to Tion cloud: {err}") from err

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NeoTionConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register custom services (Actions)."""
    
    async def handle_set_breezer(call: ServiceCall) -> None:
        """Handle the set_breezer action."""
        entity_ids = call.data["entity_id"]
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        mode = call.data.get("mode")
        target_co2 = call.data.get("targetco2")
        speed = call.data.get("speed")
        target_temp = call.data.get("targettemp")
        heat = call.data.get("heat")
        swing = call.data.get("swing")

        # П.3: Если нет ни одного параметра, просто выходим
        if all(v is None for v in [mode, target_co2, speed, target_temp, heat, swing]):
            return

        entity_registry = er.async_get(hass)

        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator: TionDataUpdateCoordinator = entry.runtime_data
            changed = False

            for entity_id in entity_ids:
                registry_entry = entity_registry.async_get(entity_id)
                if not registry_entry or not registry_entry.unique_id.endswith("_climate"):
                    continue
                
                guid = registry_entry.unique_id.replace("_climate", "")
                device = coordinator.devices.get(guid)
                if not device:
                    continue

                # П.2: Если параметр не указан, не меняем его
                if mode:
                    if mode == "off":
                        device.speed = 0
                        if hasattr(device, "swing"):
                            device.swing.mode = "horizontal" # По вашей логике
                    elif mode == "fan":
                        device.zone.mode = "manual"
                        if speed is not None:
                            device.speed = int(speed)
                        elif getattr(device, "speed", 0) == 0:
                            device.speed = 1 # Включаем на 1 скорость, если было выключено
                    elif mode == "auto":
                        device.zone.mode = "auto"
                        if speed is not None:
                            device.zone.min_speed = 0
                            device.zone.max_speed = int(speed)
                        if hasattr(device, "swing"):
                            device.swing.mode = "horizontal" # По вашей логике

                if target_co2 is not None:
                    if getattr(device, "zone", None):
                        device.zone.target_co2 = int(target_co2)

                # Если скорость задана БЕЗ mode, принудительно ставим manual
                if speed is not None and not mode:
                    device.zone.mode = "manual"
                    device.speed = int(speed)

                if target_temp is not None:
                    device.heater_temp = int(target_temp)

                if heat is not None:
                    device.heater_enabled = heat

                if swing is not None:
                    if hasattr(device, "swing"):
                        device.swing.mode = str(swing).lower()

                await hass.async_add_executor_job(device.send)
                changed = True

            if changed:
                await coordinator.async_fast_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_breezer",
        handle_set_breezer,
        schema=vol.Schema({
            vol.Required("entity_id"): cv.entity_ids,
            vol.Optional("mode"): vol.In(["off", "fan", "auto"]),
            vol.Optional("targetco2"): vol.Coerce(int),
            vol.Optional("speed"): vol.All(vol.Coerce(int), vol.Range(min=1, max=6)),
            vol.Optional("targettemp"): vol.All(vol.Coerce(int), vol.Range(min=10, max=30)),
            vol.Optional("heat"): cv.boolean,
            vol.Optional("swing"): vol.In(["off", "horizontal", "vertical", "both"]),
        }),
    )

    return True