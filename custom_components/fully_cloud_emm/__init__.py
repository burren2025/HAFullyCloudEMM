"""The Fully Cloud EMM integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import FullyCloudClient
from .const import (
    ATTR_DEVID,
    ATTR_NOWAIT,
    ATTR_QUEUE_OFFLINE,
    CONF_API_EMAIL,
    CONF_API_KEY,
    DOMAIN,
    PLATFORMS,
    SERVICE_REBOOT_DEVICE,
    SERVICE_REFRESH,
    SERVICE_RESTART_APP,
)
from .coordinator import FullyCloudCoordinator

type FullyCloudConfigEntry = ConfigEntry[FullyCloudCoordinator]

_LOGGER = logging.getLogger(__name__)

COMMAND_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.ensure_list,
        vol.Optional(ATTR_DEVID): cv.ensure_list,
        vol.Optional(ATTR_QUEUE_OFFLINE, default=False): cv.boolean,
        vol.Optional(ATTR_NOWAIT, default=True): cv.boolean,
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
        SERVICE_RESTART_APP,
        _command_service_handler(hass, "restartApp"),
        schema=COMMAND_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REBOOT_DEVICE,
        _command_service_handler(hass, "rebootDevice"),
        schema=COMMAND_SERVICE_SCHEMA,
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: FullyCloudConfigEntry
) -> bool:
    """Set up Fully Cloud EMM from a config entry."""
    client = FullyCloudClient(
        async_get_clientsession(hass),
        entry.data[CONF_API_EMAIL],
        entry.data[CONF_API_KEY],
    )
    coordinator = FullyCloudCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FullyCloudConfigEntry
) -> bool:
    """Unload Fully Cloud EMM."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


def _command_service_handler(hass: HomeAssistant, command: str):
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
            try:
                results = await coordinator.client.async_send_command(
                    command,
                    sorted(device_ids),
                    persistent=call.data[ATTR_QUEUE_OFFLINE],
                    nowait=call.data[ATTR_NOWAIT],
                )
            except HomeAssistantError:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "Fully Cloud command %s failed for %s: %s",
                    command,
                    ", ".join(device_labels),
                    err,
                )
                raise HomeAssistantError(
                    f"Fully Cloud command {command} failed: {err}"
                ) from err

            _LOGGER.info(
                "Fully Cloud command %s sent to %s: %s",
                command,
                ", ".join(device_labels),
                _command_result_summary(results),
            )

    return async_handle_command


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
        status = str(result.get("status") or "unknown")
        message = str(
            result.get("statustext")
            or result.get("message")
            or result.get("error")
            or ""
        ).strip()
        if message:
            summaries.append(f"{status}: {_short_log_text(message)}")
        else:
            summaries.append(status)

    return "; ".join(summaries)


def _short_log_text(value: str) -> str:
    """Return a short single-line value for logs."""
    return " ".join(value.split())[:200]
