"""The Neo Tion integration."""

from __future__ import annotations

import logging
import asyncio
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

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
        _LOGGER.debug("Action set_breezer called with data: %s", call.data)
        
        entity_ids = call.data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        mode = call.data.get("mode")
        target_co2 = call.data.get("targetco2")
        speed = call.data.get("speed")
        target_temp = call.data.get("targettemp")
        heat = call.data.get("heat")
        swing = call.data.get("swing")

        if all(v is None for v in [mode, target_co2, speed, target_temp, heat, swing]):
            _LOGGER.debug("No parameters provided, exiting")
            return

        climate_component = hass.data.get("entity_components", {}).get("climate")
        if not climate_component:
            _LOGGER.error("Climate component not found")
            return

        for entity_id in entity_ids:
            entity = climate_component.get_entity(entity_id)
            if not entity or not hasattr(entity, "_device_guid"):
                _LOGGER.warning("Entity %s is not a Tion breezer", entity_id)
                continue
            
            guid = entity._device_guid
            coordinator = None
            
            for entry in hass.config_entries.async_entries(DOMAIN):
                if guid in entry.runtime_data.devices:
                    coordinator = entry.runtime_data
                    break
            
            if not coordinator:
                _LOGGER.error("Coordinator not found for device %s", guid)
                continue

            device = coordinator.devices.get(guid)
            if not device:
                _LOGGER.error("Device %s not found in coordinator", guid)
                continue

            _LOGGER.debug("Applying changes to %s", getattr(device, "name", guid))

            # Определяем текущий режим бризера
            current_zone = getattr(device, "zone", None)
            current_mode = getattr(current_zone, "mode", "manual") if current_zone else "manual"
            
            # Целевой режим (если не передан, сохраняем текущий)
            if mode == "off":
                target_mode = "off"
            elif mode == "fan":
                target_mode = "manual"
            elif mode == "auto":
                target_mode = "auto"
            else:
                target_mode = current_mode

            # --- ШАГ 1: Зона (режим и CO2) ---
            zone_changed = False
            
            if mode is not None and mode != "off":
                if current_zone and current_zone.mode != target_mode:
                    current_zone.mode = target_mode
                    zone_changed = True

            if target_co2 is not None and current_zone:
                current_zone.target_co2 = int(target_co2)
                zone_changed = True

            if zone_changed:
                _LOGGER.debug("Sending zone mode command to %s", getattr(device, "name", guid))
                try:
                    await hass.async_add_executor_job(device.send)
                    await asyncio.sleep(2)
                except Exception as err:
                    _LOGGER.error("Failed to send zone command: %s", err)

            # --- ШАГ 2: Скорость ---
            speed_changed = False
            
            if mode == "off":
                if getattr(device, "speed", 0) != 0:
                    device.speed = 0
                    speed_changed = True
            elif speed is not None:
                if target_mode == "auto":
                    # В авто-режиме меняем границы, а не текущую скорость
                    device.speed_min_set = 0
                    device.speed_max_set = int(speed)
                    if getattr(device, "speed", 0) == 0:
                        device.speed = 1
                    speed_changed = True
                else:
                    # В ручном режиме меняем фиксированную скорость
                    device.speed = int(speed)
                    speed_changed = True
            elif mode == "fan" and speed is None:
                if getattr(device, "speed", 0) == 0:
                    device.speed = 1
                    speed_changed = True

            if speed_changed:
                _LOGGER.debug("Sending speed command (%s) to %s", device.speed, getattr(device, "name", guid))
                try:
                    await hass.async_add_executor_job(device.send)
                    await asyncio.sleep(2)
                except Exception as err:
                    _LOGGER.error("Failed to send speed command: %s", err)

            # --- ШАГ 3: Жалюзи ---
            target_swing = None
            if swing is not None:
                target_swing = str(swing).lower()
                if target_swing == "indoor":
                    target_swing = "vertical"
                elif target_swing == "outdoor":
                    target_swing = "horizontal"
            
            # Принудительно ставим horizontal, если режим off или auto
            if target_mode in ("off", "auto"):
                target_swing = "horizontal"

            if target_swing is not None:
                current_swing = str(getattr(getattr(device, "swing", None), "mode", "horizontal")).lower()
                if current_swing != target_swing and hasattr(device, "swing"):
                    device.swing.mode = target_swing
                    _LOGGER.debug("Sending swing command (%s) to %s", target_swing, getattr(device, "name", guid))
                    try:
                        await hass.async_add_executor_job(device.send)
                        await asyncio.sleep(2)
                    except Exception as err:
                        _LOGGER.error("Failed to send swing command: %s", err)

            # --- ШАГ 4: Обогрев и температура ---
            heater_changed = False
            if target_temp is not None:
                if getattr(device, "t_set", 0) != int(target_temp) or not getattr(device, "heater_enabled", False):
                    device.t_set = int(target_temp)
                    device.heater_enabled = True
                    heater_changed = True
                    if getattr(device, "speed", 0) == 0:
                        device.speed = 1

            if heat is not None:
                if getattr(device, "heater_enabled", False) != heat:
                    device.heater_enabled = heat
                    heater_changed = True
                    if heat and getattr(device, "speed", 0) == 0:
                        device.speed = 1

            if heater_changed:
                _LOGGER.debug("Sending heater/temp command to %s", getattr(device, "name", guid))
                try:
                    await hass.async_add_executor_job(device.send)
                except Exception as err:
                    _LOGGER.error("Failed to send heater/temp command: %s", err)

            hass.async_create_task(coordinator.async_fast_refresh())

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
            vol.Optional("swing"): vol.In(["indoor", "outdoor", "both"]),
        }),
    )

    return True