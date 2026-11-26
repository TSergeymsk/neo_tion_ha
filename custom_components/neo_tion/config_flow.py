"""Config flow for Neo Tion."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import create_tion_api

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class NeoTionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neo Tion."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._validate_credentials(user_input)
            except InvalidAuth as err:
                _LOGGER.warning("Tion auth failed: %s", err)
                errors["base"] = "invalid_auth"
            except NoDevicesFound as err:
                _LOGGER.warning("Tion auth OK but no devices: %s", err)
                errors["base"] = "no_devices"
            except Exception:
                _LOGGER.exception(
                    "Unexpected exception during Tion authentication"
                )
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    user_input[CONF_EMAIL].lower()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _validate_credentials(self, data: dict[str, Any]) -> None:
        """Validate the credentials by trying to fetch devices."""
        try:
            await self.hass.async_add_executor_job(
                self._sync_validate,
                data[CONF_EMAIL],
                data[CONF_PASSWORD],
            )
        except NoDevicesFound:
            raise
        except Exception as err:
            # Полный трейсбек в журнал — иначе причина сбоя не видна
            _LOGGER.exception(
                "Tion authentication raised an exception: %s", err
            )
            raise InvalidAuth(str(err)) from err

    @staticmethod
    def _sync_validate(email: str, password: str) -> None:
        """Synchronous credential validation (runs in executor)."""
        api = create_tion_api(email, password)
        devices = api.get_devices()
        if not devices:
            raise NoDevicesFound(
                "Authentication succeeded, but no devices were returned. "
                "Check that devices are linked to the account and are online."
            )


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid credentials or auth failure."""


class NoDevicesFound(HomeAssistantError):
    """Error to indicate successful auth but empty device list."""