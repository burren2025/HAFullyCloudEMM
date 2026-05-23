"""Client for the Fully Cloud REST API."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
from yarl import URL

from .const import API_BASE_URL


class FullyCloudError(Exception):
    """Base error for Fully Cloud API failures."""


class FullyCloudAuthError(FullyCloudError):
    """Raised when Fully Cloud rejects credentials."""


class FullyCloudClient:
    """Small async client for Fully Cloud device status."""

    def __init__(
        self,
        session: ClientSession,
        api_email: str,
        api_key: str,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._session = session
        self._api_email = api_email
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return all devices visible to the configured Fully Cloud token."""
        url = URL(f"{self._base_url}/devices").with_query(
            {"apiemail": self._api_email, "apikey": self._api_key}
        )

        try:
            response = await self._session.get(url, timeout=30)
            response.raise_for_status()
            payload = await response.json(content_type=None)
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise FullyCloudAuthError("Fully Cloud rejected the credentials") from err
            raise FullyCloudError(f"Fully Cloud returned HTTP {err.status}") from err
        except ClientError as err:
            raise FullyCloudError("Could not connect to Fully Cloud") from err
        except TimeoutError as err:
            raise FullyCloudError("Timed out connecting to Fully Cloud") from err

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

