"""Data update coordinator for Fully Cloud EMM."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FullyCloudClient, FullyCloudError, _redact_message
from .local_api import FullyLocalClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

MAX_FLATTEN_DEPTH = 8
MAX_FLATTEN_FIELDS = 500


@dataclass(frozen=True)
class FullyCloudDevice:
    """Normalized Fully Cloud device payload."""

    device_id: str
    name: str
    payload: dict[str, Any]
    fields: dict[str, Any]


class FullyCloudCoordinator(DataUpdateCoordinator[dict[str, FullyCloudDevice]]):
    """Fetch and normalize Fully Cloud devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FullyCloudClient | None,
        local_clients: tuple[FullyLocalClient, ...] = (),
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.local_clients = local_clients
        self.local_clients_by_device_id: dict[str, FullyLocalClient] = {}

    async def _async_update_data(self) -> dict[str, FullyCloudDevice]:
        normalized: dict[str, FullyCloudDevice] = {}

        if self.client is not None:
            try:
                devices = await self.client.async_get_devices()
            except FullyCloudError as err:
                raise UpdateFailed(str(err)) from err

            for index, payload in enumerate(devices, start=1):
                device_id = _device_id(payload, index)
                normalized[device_id] = _normalized_device(device_id, payload)

        self.local_clients_by_device_id = {}
        for index, local_client in enumerate(self.local_clients, start=1):
            configured_id = local_client.config.cloud_device_id
            try:
                local_payload = await local_client.async_get_device_info()
            except FullyCloudError as err:
                if configured_id and configured_id in normalized:
                    normalized[configured_id] = _with_local_payload(
                        normalized[configured_id],
                        {"local_api_connected": False},
                    )
                _LOGGER.debug(
                    "Fully local API refresh failed for %s: %s",
                    configured_id or local_client.config.base_url,
                    _redact_message(str(err)),
                )
                continue

            local_device_id = configured_id or _device_id(local_payload, index)
            self.local_clients_by_device_id[local_device_id] = local_client
            local_wrapper = {
                "local_api_connected": True,
                "local_device_info": local_payload,
            }
            if local_device_id in normalized:
                normalized[local_device_id] = _with_local_payload(
                    normalized[local_device_id], local_wrapper
                )
            else:
                normalized[local_device_id] = _normalized_device(
                    local_device_id,
                    local_wrapper,
                    name=_device_name(local_payload, local_device_id),
                )

        return normalized

    def local_client_for_device(self, device_id: str) -> FullyLocalClient | None:
        """Return the local API client for a Fully device ID, if configured."""
        return self.local_clients_by_device_id.get(device_id)


def _normalized_device(
    device_id: str, payload: dict[str, Any], *, name: str | None = None
) -> FullyCloudDevice:
    return FullyCloudDevice(
        device_id=device_id,
        name=name or _device_name(payload, device_id),
        payload=payload,
        fields=_flatten_payload(payload),
    )


def _with_local_payload(
    device: FullyCloudDevice, local_payload: dict[str, Any]
) -> FullyCloudDevice:
    payload = dict(device.payload)
    payload.update(local_payload)
    return _normalized_device(device.device_id, payload, name=device.name)


def _device_id(payload: Mapping[str, Any], fallback_index: int) -> str:
    for key in ("devid", "deviceId", "deviceID", "device_id", "id", "androidId"):
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

    def add_field(key: str, value: Any) -> bool:
        if not key or len(fields) >= MAX_FLATTEN_FIELDS:
            return False
        fields[key] = value
        return True

    def flatten(prefix: str, value: Any, depth: int) -> None:
        if len(fields) >= MAX_FLATTEN_FIELDS:
            return

        if depth >= MAX_FLATTEN_DEPTH:
            add_field(prefix, _safe_leaf_value(value))
            return

        if isinstance(value, Mapping):
            if not value:
                add_field(prefix, {})
                return
            for nested_key, nested_value in value.items():
                key = _field_key(str(nested_key))
                flatten(f"{prefix}_{key}" if prefix else key, nested_value, depth + 1)
            return

        if isinstance(value, list):
            if not value:
                add_field(prefix, [])
                return
            for position, nested_value in enumerate(value):
                flatten(f"{prefix}_{position + 1}", nested_value, depth + 1)
            return

        add_field(prefix, value)

    flatten("", payload, 0)
    return {key: value for key, value in fields.items() if key}


def _safe_leaf_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return "[object]"
    if isinstance(value, list):
        return "[list]"
    return value


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
