"""Diagnostics for Fully Cloud EMM."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import CONF_API_EMAIL, CONF_API_KEY, CONF_LOCAL_DEVICES
from .coordinator import FullyCloudCoordinator

TO_REDACT = {
    CONF_API_EMAIL,
    CONF_API_KEY,
    CONF_LOCAL_DEVICES,
    "apikey",
    "apiemail",
    "email",
    "password",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[FullyCloudCoordinator]
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {key: _redact(key, value) for key, value in entry.data.items()},
        "options": {key: _redact(key, value) for key, value in entry.options.items()},
        "device_count": len(coordinator.data),
        "devices": {
            device_id: _redact_payload(device.payload)
            for device_id, device in coordinator.data.items()
        },
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[FullyCloudCoordinator],
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    coordinator = entry.runtime_data
    for _, device_id in device.identifiers:
        fully_device = coordinator.data.get(device_id)
        if fully_device:
            return _redact_payload(fully_device.payload)
    return {}


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _redact(key, value) for key, value in payload.items()}


def _redact(key: str, value: Any) -> Any:
    normalized_key = key.lower()
    if normalized_key in TO_REDACT or "key" in normalized_key or "token" in normalized_key:
        return "**REDACTED**"
    if isinstance(value, dict):
        return _redact_payload(value)
    if isinstance(value, list):
        return [_redact(key, item) for item in value]
    return value

