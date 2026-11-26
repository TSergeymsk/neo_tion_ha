"""Config flow for Neo Tion."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from tion import TionApi  # type: ignore

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class Neo TionConfigFlow(ConfigFlow, domain=DOMAIN):
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
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception during Tion authentication")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _validate_credentials(self, data: dict[str, Any]) -> None:
        """Validate the credentials by trying to fetch devices."""
        try:
            await self.hass.async_add_executor_job(
                self._sync_validate, data[CONF_EMAIL], data[CONF_PASSWORD]
            )
        except Exception as err:
            raise InvalidAuth from err

    @staticmethod
    def _sync_validate(email: str, password: str) -> None:
        api = TionApi(email, password, save_auth=False)
        api.get_devices()


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid credentials."""