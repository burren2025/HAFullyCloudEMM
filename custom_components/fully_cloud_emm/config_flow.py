"""Config flow for Fully Cloud EMM."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FullyCloudAuthError, FullyCloudClient, FullyCloudError
from .const import CONF_API_EMAIL, CONF_API_KEY, DOMAIN


class FullyCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Fully Cloud EMM config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_email = user_input[CONF_API_EMAIL].strip()
            api_key = user_input[CONF_API_KEY].strip()

            await self.async_set_unique_id(api_email.lower())
            self._abort_if_unique_id_configured()

            client = FullyCloudClient(
                async_get_clientsession(self.hass), api_email, api_key
            )
            try:
                await client.async_get_devices()
            except FullyCloudAuthError:
                errors["base"] = "invalid_auth"
            except FullyCloudError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=api_email,
                    data={CONF_API_EMAIL: api_email, CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_EMAIL): str,
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )

