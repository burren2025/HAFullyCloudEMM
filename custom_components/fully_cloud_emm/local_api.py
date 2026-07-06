"""Client for the Fully Kiosk local Remote Admin API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from json import JSONDecodeError
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
from yarl import URL

from .api import (
    REQUEST_TIMEOUT,
    FullyCloudAuthError,
    FullyCloudError,
    _parse_command_response,
    _redact_message,
    _serialize_command_parameters,
    _summarize_text,
)
from .const import DEFAULT_LOCAL_API_PORT


@dataclass(frozen=True)
class FullyLocalDeviceConfig:
    """Connection details for a local Fully Kiosk device."""

    base_url: str
    password: str = ""
    cloud_device_id: str | None = None


class FullyLocalClient:
    """Small async client for one Fully Kiosk local Remote Admin endpoint."""

    def __init__(
        self,
        session: ClientSession,
        config: FullyLocalDeviceConfig,
    ) -> None:
        self._session = session
        self.config = config
        self._base_url = URL(config.base_url)

    async def async_get_device_info(self) -> dict[str, Any]:
        """Return local deviceInfo data."""
        payload = await self._async_request("deviceInfo")
        if isinstance(payload, dict):
            return payload

        raise FullyCloudError("Fully local API returned an unexpected deviceInfo response")

    async def async_send_command(
        self,
        command: str,
        *,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Send a Fully Remote Admin command to the local device."""
        payload = await self._async_request(command, parameters=parameters)
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, str):
            return _parse_command_response(payload)
        return []

    async def _async_request(
        self,
        command: str,
        *,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        query = {"cmd": command, "type": "json"}
        if self.config.password:
            query["password"] = self.config.password
        if parameters:
            query.update(_serialize_command_parameters(parameters))

        try:
            response = await self._session.get(
                self._base_url, params=query, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            text = await response.text()
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise FullyCloudAuthError("Fully local API rejected the password") from err
            raise FullyCloudError(f"Fully local API returned HTTP {err.status}") from err
        except ClientError as err:
            message = _redact_message(str(err))
            raise FullyCloudError(f"Could not connect to Fully local API: {message}") from err
        except asyncio.TimeoutError as err:
            raise FullyCloudError("Timed out connecting to Fully local API") from err

        try:
            payload = json.loads(text)
        except JSONDecodeError:
            return _summarize_text(text)

        message = _local_error_message(payload)
        if message:
            if "password" in message.lower() or "auth" in message.lower():
                raise FullyCloudAuthError(message)
            raise FullyCloudError(message)

        return payload


def parse_local_device_options(value: str) -> tuple[FullyLocalDeviceConfig, ...]:
    """Parse local device option lines."""
    configs: list[FullyLocalDeviceConfig] = []
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = _split_local_device_line(line)
        if len(parts) == 1:
            cloud_device_id = None
            base_url = parts[0]
            password = ""
        elif len(parts) == 2 and (
            _looks_like_local_url(parts[0]) or not _looks_like_local_url(parts[1])
        ):
            cloud_device_id = None
            base_url, password = parts
        elif len(parts) == 2:
            cloud_device_id, base_url = parts
            password = ""
        else:
            cloud_device_id, base_url, password = parts[:3]

        try:
            normalized_url = _normalize_local_base_url(base_url)
        except ValueError as err:
            raise ValueError(f"Line {line_number}: {err}") from err

        configs.append(
            FullyLocalDeviceConfig(
                base_url=normalized_url,
                password=password,
                cloud_device_id=cloud_device_id or None,
            )
        )

    return tuple(configs)


def _split_local_device_line(value: str) -> list[str]:
    separator = "|" if "|" in value else ","
    return [part.strip() for part in value.split(separator, 2)]


def _looks_like_local_url(value: str) -> bool:
    text = value.strip().lower()
    return "://" in text or "." in text or text.startswith(("localhost", "["))


def _normalize_local_base_url(value: str) -> str:
    raw_url = value.strip()
    if not raw_url:
        raise ValueError("local device URL is empty")
    if "://" not in raw_url:
        raw_url = f"http://{raw_url}"

    url = URL(raw_url)
    if not url.host:
        raise ValueError("local device URL must include a host or IP address")
    if url.scheme not in {"http", "https"}:
        raise ValueError("local device URL must use http or https")
    if url.port is None:
        url = url.with_port(DEFAULT_LOCAL_API_PORT)
    if not url.path:
        url = url.with_path("/")

    return str(url)


def _local_error_message(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    for key in ("error", "errorMessage", "error_message", "statustext", "message"):
        value = payload.get(key)
        if value not in (None, "") and _looks_like_error(value):
            return _redact_message(str(value))

    status = payload.get("status")
    if isinstance(status, str) and status.lower() in {"error", "failed", "failure"}:
        return _redact_message(str(payload))

    return None


def _looks_like_error(value: Any) -> bool:
    text = str(value).lower()
    return any(marker in text for marker in ("error", "failed", "failure", "wrong"))
