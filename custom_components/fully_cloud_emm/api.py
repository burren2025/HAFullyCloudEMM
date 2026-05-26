"""Client for the Fully Cloud REST API."""

from __future__ import annotations

import json
import logging
import re
from json import JSONDecodeError
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
from yarl import URL

from .const import API_BASE_URLS, API_REMOTE_URL

_LOGGER = logging.getLogger(__name__)


class FullyCloudError(Exception):
    """Base error for Fully Cloud API failures."""


class FullyCloudAuthError(FullyCloudError):
    """Raised when Fully Cloud rejects credentials."""


SENSITIVE_QUERY_RE = re.compile(
    r"(?i)((?:apiemail|apikey|token|key|password|secret)=)([^&\s]+)"
)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


class FullyCloudClient:
    """Small async client for Fully Cloud device status."""

    def __init__(
        self,
        session: ClientSession,
        api_email: str,
        api_key: str,
        base_urls: tuple[str, ...] = API_BASE_URLS,
    ) -> None:
        self._session = session
        self._api_email = api_email
        self._api_key = api_key
        self._base_urls = tuple(base_url.rstrip("/") for base_url in base_urls)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return all devices visible to the configured Fully Cloud token."""
        failures: list[str] = []
        auth_failures: list[str] = []

        for base_url in self._base_urls:
            try:
                return await self._async_get_devices_from_url(base_url)
            except FullyCloudAuthError as err:
                auth_failures.append(f"{base_url}: {_redact_message(str(err))}")
                _LOGGER.debug("Fully Cloud authentication failed for %s: %s", base_url, _redact_message(str(err)))
            except FullyCloudError as err:
                failures.append(f"{base_url}: {_redact_message(str(err))}")
                _LOGGER.debug("Fully Cloud request failed for %s: %s", base_url, _redact_message(str(err)))

        if failures:
            raise FullyCloudError("; ".join(failures))

        if auth_failures:
            raise FullyCloudAuthError("; ".join(auth_failures))

        raise FullyCloudError("No Fully Cloud API endpoints are configured")

    async def _async_get_devices_from_url(self, base_url: str) -> list[dict[str, Any]]:
        """Return devices from one Fully Cloud API base URL."""
        url = URL(f"{base_url}/devices").with_query(
            {"apiemail": self._api_email, "apikey": self._api_key}
        )

        try:
            response = await self._session.get(url, timeout=30)
            response.raise_for_status()
            text = await response.text()
            payload = json.loads(text)
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise FullyCloudAuthError("Fully Cloud rejected the credentials") from err
            raise FullyCloudError(f"Fully Cloud returned HTTP {err.status}") from err
        except JSONDecodeError as err:
            raise FullyCloudError(
                f"Fully Cloud returned non-JSON response: {_redact_message(_summarize_text(text))}"
            ) from err
        except ClientError as err:
            raise FullyCloudError(f"Could not connect to Fully Cloud: {err}") from err
        except TimeoutError as err:
            raise FullyCloudError("Timed out connecting to Fully Cloud") from err

        if isinstance(payload, dict):
            devices_payload = payload.get("devices")
            if isinstance(devices_payload, list):
                payload = devices_payload
            else:
                message = _error_message(payload)
                if message:
                    if "auth" in message.lower() or "key" in message.lower():
                        raise FullyCloudAuthError(message)
                    raise FullyCloudError(message)

        if isinstance(payload, dict) and payload.get("error"):
            message = str(payload["error"])
            if "auth" in message.lower() or "key" in message.lower():
                raise FullyCloudAuthError(message)
            raise FullyCloudError(message)

        if not isinstance(payload, list):
            raise FullyCloudError("Fully Cloud returned an unexpected response")

        devices: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                devices.append(item)

        return devices

    async def async_send_command(
        self,
        command: str,
        device_ids: list[str],
        *,
        persistent: bool = False,
        nowait: bool = True,
    ) -> list[dict[str, Any]]:
        """Send a Fully Remote Admin command through Fully Cloud."""
        if not device_ids:
            raise FullyCloudError("No Fully Cloud devices were selected")

        query = {
            "apiemail": self._api_email,
            "apikey": self._api_key,
            "devid": ",".join(device_ids),
            "cmd": command,
            "persistent": "1" if persistent else "0",
            "nowait": "1" if nowait else "0",
        }
        url = URL(API_REMOTE_URL).with_query(query)

        try:
            response = await self._session.get(url, timeout=30)
            response.raise_for_status()
            text = await response.text()
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise FullyCloudAuthError("Fully Cloud rejected the credentials") from err
            raise FullyCloudError(f"Fully Cloud returned HTTP {err.status}") from err
        except ClientError as err:
            raise FullyCloudError(f"Could not connect to Fully Cloud: {err}") from err
        except TimeoutError as err:
            raise FullyCloudError("Timed out connecting to Fully Cloud") from err

        results = _parse_command_response(text)
        failures = [
            result
            for result in results
            if str(result.get("status", "")).lower() in {"error", "failed", "failure"}
        ]
        if failures:
            messages = [
                str(result.get("statustext") or result.get("error") or result)
                for result in failures
            ]
            message = _redact_message("; ".join(messages))
            if "auth" in message.lower() or "key" in message.lower():
                raise FullyCloudAuthError(message)
            raise FullyCloudError(message)

        return results


def _summarize_text(value: str) -> str:
    """Return a short, log-safe response summary."""
    return " ".join(value.split())[:200]


def _redact_message(value: str) -> str:
    """Redact credentials and email addresses from API-provided text."""
    value = SENSITIVE_QUERY_RE.sub(r"\1**REDACTED**", value)
    return EMAIL_RE.sub("**REDACTED_EMAIL**", value)


def _parse_command_response(value: str) -> list[dict[str, Any]]:
    """Parse the line-delimited JSON response from the Fully remote endpoint."""
    stripped = value.strip()
    if not stripped:
        return []

    try:
        payload = json.loads(stripped)
    except JSONDecodeError:
        results: list[dict[str, Any]] = []
        for line in stripped.splitlines():
            try:
                line_payload = json.loads(line)
            except JSONDecodeError:
                results.append({"status": "OK", "statustext": _summarize_text(line)})
                continue
            if isinstance(line_payload, dict):
                results.append(line_payload)
        return results

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        return [payload]

    return [{"status": "OK", "statustext": _summarize_text(stripped)}]


def _error_message(payload: dict[str, Any]) -> str | None:
    """Return an API error message from a Fully Cloud response."""
    for key in ("error", "errorMessage", "error_message"):
        value = payload.get(key)
        if value not in (None, ""):
            return _redact_message(str(value))

    status = payload.get("status")
    if isinstance(status, str) and status.lower() in {"error", "failed", "failure"}:
        return _redact_message(str(payload))

    return None
