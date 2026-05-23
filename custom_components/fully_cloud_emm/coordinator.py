"""Data update coordinator for Fully Cloud EMM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FullyCloudClient, FullyCloudError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FullyCloudDevice:
    """Normalized Fully Cloud device payload."""

    device_id: str
    name: str
    payload: dict[str, Any]
    fields: dict[str, Any]


class FullyCloudCoordinator(DataUpdateCoordinator[dict[str, FullyCloudDevice]]):
    """Fetch and normalize Fully Cloud devices."""

    def __init__(self, hass: HomeAssistant, client: FullyCloudClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, FullyCloudDevice]:
        try:
            devices = await self.client.async_get_devices()
        except FullyCloudError as err:
            raise UpdateFailed(str(err)) from err

        normalized: dict[str, FullyCloudDevice] = {}
        for index, payload in enumerate(devices, start=1):
            device_id = _device_id(payload, index)
            normalized[device_id] = FullyCloudDevice(
                device_id=device_id,
                name=_device_name(payload, device_id),
                payload=payload,
                fields=_flatten_payload(payload),
            )

        return normalized


def _device_id(payload: Mapping[str, Any], fallback_index: int) -> str:
    for key in ("devid", "deviceId", "device_id", "id", "androidId"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)

    return f"device_{fallback_index}"


def _device_name(payload: Mapping[str, Any], device_id: str) -> str:
    for key in ("deviceName", "name", "alias", "label", "model"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)

    return f"Fully Cloud {device_id}"


def _flatten_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    def flatten(prefix: str, value: Any) -> None:
        if isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                key = _field_key(str(nested_key))
                flatten(f"{prefix}_{key}" if prefix else key, nested_value)
            return

        if isinstance(value, list):
            for position, nested_value in enumerate(value):
                flatten(f"{prefix}_{position + 1}", nested_value)
            if not value:
                fields[prefix] = []
            return

        fields[prefix] = value

    flatten("", payload)
    return {key: value for key, value in fields.items() if key}


def _field_key(value: str) -> str:
    output = []
    previous_lower = False
    for character in value.strip():
        if character.isupper() and previous_lower:
            output.append("_")
        if character.isalnum():
            output.append(character.lower())
            previous_lower = character.islower() or character.isdigit()
        else:
            if output and output[-1] != "_":
                output.append("_")
            previous_lower = False

    return "".join(output).strip("_")
