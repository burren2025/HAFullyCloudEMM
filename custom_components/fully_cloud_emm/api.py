"""Client for the Fully Cloud REST API."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ContentTypeError
from yarl import URL

from .const import API_BASE_URLS

_LOGGER = logging.getLogger(__name__)


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
        base_urls: tuple[str, ...] = API_BASE_URLS,
    ) -> None:
        self._session = session
        self._api_email = api_email
        self._api_key = api_key
        self._base_urls = tuple(base_url.rstrip("/") for base_url in base_urls)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return all devices visible to the configured Fully Cloud token."""
        last_error: FullyCloudError | None = None

        for base_url in self._base_urls:
            try:
                return await self._async_get_devices_from_url(base_url)
            except FullyCloudAuthError:
                raise
            except FullyCloudError as err:
                last_error = err
                _LOGGER.debug("Fully Cloud request failed for %s: %s", base_url, err)

        if last_error is not None:
            raise last_error

        raise FullyCloudError("No Fully Cloud API endpoints are configured")

    async def _async_get_devices_from_url(self, base_url: str) -> list[dict[str, Any]]:
        """Return devices from one Fully Cloud API base URL."""
        url = URL(f"{base_url}/devices").with_query(
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
        except ContentTypeError as err:
            text = await response.text()
            raise FullyCloudError(
                f"Fully Cloud returned non-JSON response: {_summarize_text(text)}"
            ) from err
        except ClientError as err:
            raise FullyCloudError(f"Could not connect to Fully Cloud: {err}") from err
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


def _summarize_text(value: str) -> str:
    """Return a short, log-safe response summary."""
    return " ".join(value.split())[:200]
