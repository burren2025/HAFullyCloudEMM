"""The Fully Cloud EMM integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import FullyCloudClient, _redact_message
from .const import (
    ATTR_ACTION,
    ATTR_DEVID,
    ATTR_ENGINE,
    ATTR_FOCUS,
    ATTR_LEVEL,
    ATTR_LOCALE,
    ATTR_NEW_TAB,
    ATTR_NOWAIT,
    ATTR_PACKAGE,
    ATTR_QUEUE,
    ATTR_QUEUE_OFFLINE,
    ATTR_STREAM,
    ATTR_TAB,
    ATTR_TEXT,
    ATTR_URL,
    CONF_API_EMAIL,
    CONF_API_KEY,
    CONF_LOCAL_DEVICES,
    DOMAIN,
    PLATFORMS,
    SERVICE_LOAD_START_URL,
    SERVICE_LOAD_URL,
    SERVICE_REBOOT_DEVICE,
    SERVICE_REFRESH,
    SERVICE_REFRESH_DEVICE,
    SERVICE_RESTART_APP,
    SERVICE_SCREEN_OFF,
    SERVICE_SCREEN_ON,
    SERVICE_SET_AUDIO_VOLUME,
    SERVICE_SET_OVERLAY_MESSAGE,
    SERVICE_START_APPLICATION,
    SERVICE_START_SCREENSAVER,
    SERVICE_STOP_SCREENSAVER,
    SERVICE_STOP_TEXT_TO_SPEECH,
    SERVICE_TEXT_TO_SPEECH,
)
from .coordinator import FullyCloudCoordinator
from .local_api import FullyLocalClient, parse_local_device_options

type FullyCloudConfigEntry = ConfigEntry[FullyCloudCoordinator]

_LOGGER = logging.getLogger(__name__)


def _command_schema(extra_fields: dict) -> vol.Schema:
    """Return a command service schema with common targeting fields."""
    schema = {
        vol.Optional(ATTR_DEVICE_ID): cv.ensure_list,
        vol.Optional(ATTR_DEVID): cv.ensure_list,
        vol.Optional(ATTR_QUEUE_OFFLINE, default=False): cv.boolean,
        vol.Optional(ATTR_NOWAIT, default=True): cv.boolean,
    }
    schema.update(extra_fields)
    return vol.Schema(schema)


COMMAND_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.ensure_list,
        vol.Optional(ATTR_DEVID): cv.ensure_list,
        vol.Optional(ATTR_QUEUE_OFFLINE, default=False): cv.boolean,
        vol.Optional(ATTR_NOWAIT, default=True): cv.boolean,
    }
)

REFRESH_DEVICE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.ensure_list,
        vol.Optional(ATTR_DEVID): cv.ensure_list,
    }
)

LOAD_URL_SERVICE_SCHEMA = _command_schema(
    {
        vol.Required(ATTR_URL): str,
        vol.Optional(ATTR_TAB): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(ATTR_FOCUS): cv.boolean,
        vol.Optional(ATTR_NEW_TAB): cv.boolean,
    }
)

OVERLAY_MESSAGE_SERVICE_SCHEMA = _command_schema({vol.Required(ATTR_TEXT): str})

START_APPLICATION_SERVICE_SCHEMA = _command_schema(
    {
        vol.Required(ATTR_PACKAGE): str,
        vol.Optional(ATTR_ACTION): str,
        vol.Optional(ATTR_URL): str,
    }
)

TEXT_TO_SPEECH_SERVICE_SCHEMA = _command_schema(
    {
        vol.Required(ATTR_TEXT): str,
        vol.Optional(ATTR_LOCALE): str,
        vol.Optional(ATTR_ENGINE): str,
        vol.Optional(ATTR_QUEUE, default=False): cv.boolean,
    }
)

SET_AUDIO_VOLUME_SERVICE_SCHEMA = _command_schema(
    {
        vol.Required(ATTR_LEVEL): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_STREAM, default=3): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Fully Cloud EMM services."""
    hass.data.setdefault(DOMAIN, {})

    async def async_refresh(call: ServiceCall) -> None:
        """Refresh every configured Fully Cloud account."""
        coordinators: list[FullyCloudCoordinator] = list(hass.data[DOMAIN].values())
        for coordinator in coordinators:
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, async_refresh)
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DEVICE,
        _refresh_device_service_handler(hass),
        schema=REFRESH_DEVICE_SERVICE_SCHEMA,
    )
    _register_command_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: FullyCloudConfigEntry
) -> bool:
    """Set up Fully Cloud EMM from a config entry."""
    session = async_get_clientsession(hass)
    client = FullyCloudClient(
        session,
        entry.data[CONF_API_EMAIL],
        entry.data[CONF_API_KEY],
    )
    local_clients = tuple(
        FullyLocalClient(session, config)
        for config in parse_local_device_options(
            entry.options.get(CONF_LOCAL_DEVICES, "")
        )
    )
    coordinator = FullyCloudCoordinator(hass, client, local_clients)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: FullyCloudConfigEntry
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: FullyCloudConfigEntry
) -> bool:
    """Unload Fully Cloud EMM."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok



def _register_command_services(hass: HomeAssistant) -> None:
    """Register Fully Remote Admin command services."""
    services: tuple[tuple[str, str, vol.Schema, Callable[[ServiceCall], dict[str, Any]]], ...] = (
        (SERVICE_LOAD_START_URL, "loadStartUrl", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_RESTART_APP, "restartApp", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_REBOOT_DEVICE, "rebootDevice", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_SCREEN_ON, "screenOn", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_SCREEN_OFF, "screenOff", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_START_SCREENSAVER, "startScreensaver", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_STOP_SCREENSAVER, "stopScreensaver", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_STOP_TEXT_TO_SPEECH, "stopTextToSpeech", COMMAND_SERVICE_SCHEMA, _no_parameters),
        (SERVICE_SET_OVERLAY_MESSAGE, "setOverlayMessage", OVERLAY_MESSAGE_SERVICE_SCHEMA, _text_parameters),
        (SERVICE_LOAD_URL, "loadUrl", LOAD_URL_SERVICE_SCHEMA, _load_url_parameters),
        (SERVICE_START_APPLICATION, "startApplication", START_APPLICATION_SERVICE_SCHEMA, _start_application_parameters),
        (SERVICE_TEXT_TO_SPEECH, "textToSpeech", TEXT_TO_SPEECH_SERVICE_SCHEMA, _text_to_speech_parameters),
        (SERVICE_SET_AUDIO_VOLUME, "setAudioVolume", SET_AUDIO_VOLUME_SERVICE_SCHEMA, _audio_volume_parameters),
    )

    for service, command, schema, parameter_builder in services:
        hass.services.async_register(
            DOMAIN,
            service,
            _command_service_handler(hass, command, parameter_builder),
            schema=schema,
        )


def _refresh_device_service_handler(hass: HomeAssistant):
    """Build a handler for refreshing selected Fully Cloud devices."""

    async def async_handle_refresh_device(call: ServiceCall) -> None:
        selected_device_ids = _fully_device_ids_from_service_call(hass, call)
        if not selected_device_ids:
            raise HomeAssistantError("No Fully Cloud EMM devices were selected")

        by_entry = _selected_devices_by_entry(hass, selected_device_ids)
        if not by_entry:
            raise HomeAssistantError(
                "Selected devices do not belong to Fully Cloud EMM"
            )

        for entry_id, device_ids in by_entry.items():
            coordinator = hass.data[DOMAIN][entry_id]
            device_labels = _device_labels(coordinator, device_ids)
            try:
                await coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.debug(
                    "Fully Cloud refresh failed for %s: %s",
                    ", ".join(device_labels),
                    _redact_message(str(err)),
                )
                raise HomeAssistantError(
                    f"Fully Cloud refresh failed: {_redact_message(str(err))}"
                ) from err


    return async_handle_refresh_device


def _command_service_handler(
    hass: HomeAssistant,
    command: str,
    parameter_builder: Callable[[ServiceCall], dict[str, Any]],
):
    """Build a handler for a Fully Cloud command service."""

    async def async_handle_command(call: ServiceCall) -> None:
        selected_device_ids = _fully_device_ids_from_service_call(hass, call)
        if not selected_device_ids:
            raise HomeAssistantError("No Fully Cloud EMM devices were selected")

        by_entry = _selected_devices_by_entry(hass, selected_device_ids)
        if not by_entry:
            raise HomeAssistantError(
                "Selected devices do not belong to Fully Cloud EMM"
            )

        for entry_id, device_ids in by_entry.items():
            coordinator = hass.data[DOMAIN][entry_id]
            device_labels = _device_labels(coordinator, device_ids)
            parameters = parameter_builder(call)
            try:
                results = []
                cloud_device_ids = set(device_ids)

                for device_id in sorted(device_ids):
                    local_client = coordinator.local_client_for_device(device_id)
                    if local_client is None:
                        continue

                    results.extend(
                        await local_client.async_send_command(
                            command, parameters=parameters
                        )
                    )
                    cloud_device_ids.discard(device_id)

                if cloud_device_ids:
                    results.extend(
                        await coordinator.client.async_send_command(
                            command,
                            sorted(cloud_device_ids),
                            parameters=parameters,
                            persistent=call.data[ATTR_QUEUE_OFFLINE],
                            nowait=call.data[ATTR_NOWAIT],
                        )
                    )
            except HomeAssistantError:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "Fully Cloud command %s failed for %s: %s",
                    command,
                    ", ".join(device_labels),
                    _redact_message(str(err)),
                )
                raise HomeAssistantError(
                    f"Fully Cloud command {command} failed: {_redact_message(str(err))}"
                ) from err

            _LOGGER.warning(
                "Fully Cloud command %s completed for %s: %s",
                command,
                ", ".join(device_labels),
                _command_result_summary(results),
            )

    return async_handle_command


def _no_parameters(call: ServiceCall) -> dict[str, Any]:
    """Return no command parameters."""
    return {}


def _text_parameters(call: ServiceCall) -> dict[str, Any]:
    """Return text parameter for a command."""
    return {"text": call.data[ATTR_TEXT]}


def _load_url_parameters(call: ServiceCall) -> dict[str, Any]:
    """Return loadUrl command parameters."""
    return {
        "url": call.data[ATTR_URL],
        "tab": call.data.get(ATTR_TAB),
        "focus": call.data.get(ATTR_FOCUS),
        "newtab": call.data.get(ATTR_NEW_TAB),
    }


def _start_application_parameters(call: ServiceCall) -> dict[str, Any]:
    """Return startApplication command parameters."""
    return {
        "package": call.data[ATTR_PACKAGE],
        "action": call.data.get(ATTR_ACTION),
        "url": call.data.get(ATTR_URL),
    }


def _text_to_speech_parameters(call: ServiceCall) -> dict[str, Any]:
    """Return textToSpeech command parameters."""
    return {
        "text": call.data[ATTR_TEXT],
        "locale": call.data.get(ATTR_LOCALE),
        "engine": call.data.get(ATTR_ENGINE),
        "queue": call.data.get(ATTR_QUEUE),
    }


def _audio_volume_parameters(call: ServiceCall) -> dict[str, Any]:
    """Return setAudioVolume command parameters."""
    return {"level": call.data[ATTR_LEVEL], "stream": call.data[ATTR_STREAM]}


def _fully_device_ids_from_service_call(
    hass: HomeAssistant, call: ServiceCall
) -> set[str]:
    """Return Fully device IDs selected by HA device field or direct devid."""
    fully_device_ids = {str(device_id) for device_id in call.data.get(ATTR_DEVID, [])}

    for ha_device_id in call.data.get(ATTR_DEVICE_ID, []):
        fully_device_ids.update(_fully_device_ids_from_ha_device(hass, ha_device_id))

    return fully_device_ids


def _fully_device_ids_from_ha_device(
    hass: HomeAssistant, ha_device_id: str
) -> set[str]:
    """Return Fully device IDs for a Home Assistant device registry ID."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(ha_device_id)
    if device is None:
        return set()

    return {
        identifier
        for domain, identifier in device.identifiers
        if domain == DOMAIN
    }


def _selected_devices_by_entry(
    hass: HomeAssistant, selected_device_ids: set[str]
) -> dict[str, set[str]]:
    """Group selected Fully device IDs by config entry."""
    grouped: dict[str, set[str]] = {}
    coordinators: dict[str, FullyCloudCoordinator] = hass.data.get(DOMAIN, {})

    for entry_id, coordinator in coordinators.items():
        available_ids = set(coordinator.data)
        matched_ids = selected_device_ids & available_ids
        if matched_ids:
            grouped[entry_id] = matched_ids

    return grouped


def _device_labels(
    coordinator: FullyCloudCoordinator, device_ids: set[str]
) -> list[str]:
    """Return readable labels for Fully device IDs."""
    labels: list[str] = []
    for device_id in sorted(device_ids):
        device = coordinator.data.get(device_id)
        if device is None:
            labels.append(device_id)
            continue

        labels.append(f"{device.name} ({device_id})")

    return labels


def _command_result_summary(results: list[dict]) -> str:
    """Return a concise command result summary for logs."""
    if not results:
        return "accepted by Fully Cloud"

    summaries: list[str] = []
    for result in results:
        status = _redact_message(
            _short_log_text(str(result.get("status") or "unknown"))
        )
        message = str(
            result.get("statustext")
            or result.get("message")
            or result.get("error")
            or ""
        ).strip()
        if message:
            summaries.append(f"{status}: {_redact_message(_short_log_text(message))}")
        else:
            summaries.append(status)

    return "; ".join(summaries)


def _short_log_text(value: str) -> str:
    """Return a short single-line value for logs."""
    return " ".join(value.split())[:200]
