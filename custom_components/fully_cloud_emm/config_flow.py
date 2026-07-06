"""Config flow for Fully Cloud EMM."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .api import FullyCloudAuthError, FullyCloudClient, FullyCloudError, _redact_message
from .const import (
    CONF_API_EMAIL,
    CONF_API_KEY,
    CONF_ENTRY_TYPE,
    CONF_LOCAL_DEVICES,
    CONF_LOCAL_HOST,
    CONF_LOCAL_PASSWORD,
    CONF_LOCAL_PORT,
    DEFAULT_LOCAL_API_PORT,
    DOMAIN,
    ENTRY_TYPE_CLOUD,
    ENTRY_TYPE_LOCAL,
)
from .local_api import (
    FullyLocalClient,
    FullyLocalDeviceConfig,
    format_local_device_option,
    parse_local_device_options,
)

_LOGGER = logging.getLogger(__name__)


class FullyCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Fully Cloud EMM config flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FullyCloudOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the cloud/local setup menu."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["cloud", "local", "local_bulk"],
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a Fully Cloud account."""
        errors: dict[str, str] = {}
        error_detail = ""

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
            except FullyCloudAuthError as err:
                error_detail = _redact_message(str(err))
                _LOGGER.warning("Fully Cloud authentication failed: %s", error_detail)
                errors["base"] = "invalid_auth"
            except FullyCloudError as err:
                error_detail = _redact_message(str(err))
                _LOGGER.warning("Fully Cloud setup failed: %s", error_detail)
                errors["base"] = "cannot_connect"
            except Exception as err:
                error_detail = _redact_message(str(err))
                _LOGGER.exception("Unexpected error during Fully Cloud setup")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=api_email,
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_CLOUD,
                        CONF_API_EMAIL: api_email,
                        CONF_API_KEY: api_key,
                    },
                )

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_EMAIL): str,
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add one local Fully Kiosk device."""
        errors: dict[str, str] = {}
        error_detail = ""

        if user_input is not None:
            host = user_input[CONF_LOCAL_HOST].strip()
            port = int(user_input[CONF_LOCAL_PORT])
            password = user_input.get(CONF_LOCAL_PASSWORD, "").strip()
            local_devices = format_local_device_option(host, port, password)
            try:
                configs = parse_local_device_options(local_devices)
                await _async_validate_local_device(self.hass, configs[0])
            except (ValueError, FullyCloudError) as err:
                error_detail = _redact_message(str(err))
                _LOGGER.warning("Fully local API setup failed: %s", error_detail)
                errors["base"] = "local_cannot_connect"
            else:
                await self.async_set_unique_id(f"local:{configs[0].base_url}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Local Fully Kiosk {host}",
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_LOCAL,
                        CONF_LOCAL_DEVICES: local_devices,
                    },
                )

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCAL_HOST): str,
                    vol.Optional(CONF_LOCAL_PORT, default=DEFAULT_LOCAL_API_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                    vol.Optional(CONF_LOCAL_PASSWORD, default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )

    async def async_step_local_bulk(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add multiple local Fully Kiosk devices."""
        errors: dict[str, str] = {}
        error_detail = ""

        if user_input is not None:
            local_devices = user_input.get(CONF_LOCAL_DEVICES, "").strip()
            try:
                configs = parse_local_device_options(local_devices)
            except ValueError as err:
                error_detail = _redact_message(str(err))
                errors["base"] = "invalid_local_devices"
            else:
                if not configs:
                    error_detail = "Enter at least one local Fully Kiosk device."
                    errors["base"] = "invalid_local_devices"
                    return self.async_show_form(
                        step_id="local_bulk",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_LOCAL_DEVICES): TextSelector(
                                    TextSelectorConfig(multiline=True)
                                ),
                            }
                        ),
                        errors=errors,
                        description_placeholders={"error_detail": error_detail},
                    )

                successes, failures = await _async_validate_local_devices_partial(
                    self.hass, configs
                )
                if failures:
                    error_detail = _bulk_failure_message(successes, failures)
                    _LOGGER.warning("Fully local bulk setup failed: %s", error_detail)
                    for config, error in failures:
                        _LOGGER.warning(
                            "Fully local API validation failed for %s: %s",
                            config.base_url,
                            _redact_message(str(error)),
                        )
                    errors["base"] = "local_bulk_partial_failure"
                else:
                    await self.async_set_unique_id(_bulk_unique_id(configs))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Local Fully Kiosk devices ({len(configs)})",
                        data={
                            CONF_ENTRY_TYPE: ENTRY_TYPE_LOCAL,
                            CONF_LOCAL_DEVICES: local_devices,
                        },
                    )

        return self.async_show_form(
            step_id="local_bulk",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCAL_DEVICES): TextSelector(
                        TextSelectorConfig(multiline=True)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )


class FullyCloudOptionsFlow(config_entries.OptionsFlow):
    """Handle Fully Cloud EMM options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage integration options."""
        errors: dict[str, str] = {}
        error_detail = ""

        if user_input is not None:
            local_devices = user_input.get(CONF_LOCAL_DEVICES, "").strip()
            try:
                configs = parse_local_device_options(local_devices)
            except ValueError as err:
                error_detail = _redact_message(str(err))
                errors["base"] = "invalid_local_devices"
            else:
                try:
                    await _async_validate_local_devices(self.hass, configs)
                except FullyCloudError as err:
                    error_detail = _redact_message(str(err))
                    _LOGGER.warning(
                        "Fully local API validation failed: %s", error_detail
                    )
                    errors["base"] = "local_cannot_connect"
                else:
                    return self.async_create_entry(
                        title="", data={CONF_LOCAL_DEVICES: local_devices}
                    )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LOCAL_DEVICES,
                        default=self._config_entry.options.get(
                            CONF_LOCAL_DEVICES,
                            self._config_entry.data.get(CONF_LOCAL_DEVICES, ""),
                        ),
                    ): TextSelector(TextSelectorConfig(multiline=True)),
                }
            ),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )


async def _async_validate_local_devices(hass, configs) -> None:
    """Validate configured local Fully Kiosk endpoints."""
    successes, failures = await _async_validate_local_devices_partial(hass, configs)
    if failures:
        raise FullyCloudError(_bulk_failure_message(successes, failures))


async def _async_validate_local_device(
    hass, config: FullyLocalDeviceConfig
) -> None:
    """Validate one local Fully Kiosk endpoint."""
    session = async_get_clientsession(hass)
    client = FullyLocalClient(session, config)
    await client.async_get_device_info()


async def _async_validate_local_devices_partial(
    hass, configs: tuple[FullyLocalDeviceConfig, ...]
) -> tuple[int, list[tuple[FullyLocalDeviceConfig, Exception]]]:
    """Validate local endpoints and return success/failure counts."""
    session = async_get_clientsession(hass)
    failures: list[tuple[FullyLocalDeviceConfig, Exception]] = []
    for config in configs:
        client = FullyLocalClient(session, config)
        try:
            await client.async_get_device_info()
        except FullyCloudError as err:
            failures.append((config, err))

    return len(configs) - len(failures), failures


def _bulk_failure_message(
    successes: int, failures: list[tuple[FullyLocalDeviceConfig, Exception]]
) -> str:
    return (
        f"Successfully validated {successes} local device(s), "
        f"but {len(failures)} failed. Check the Home Assistant log for details."
    )


def _bulk_unique_id(configs: tuple[FullyLocalDeviceConfig, ...]) -> str:
    return "local:" + ",".join(sorted(config.base_url for config in configs))
