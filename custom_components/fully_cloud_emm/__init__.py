"""The Fully Cloud EMM integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FullyCloudClient
from .const import CONF_API_EMAIL, CONF_API_KEY, DOMAIN, PLATFORMS, SERVICE_REFRESH
from .coordinator import FullyCloudCoordinator

type FullyCloudConfigEntry = ConfigEntry[FullyCloudCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Fully Cloud EMM services."""
    hass.data.setdefault(DOMAIN, {})

    async def async_refresh(call: ServiceCall) -> None:
        """Refresh every configured Fully Cloud account."""
        coordinators: list[FullyCloudCoordinator] = list(hass.data[DOMAIN].values())
        for coordinator in coordinators:
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, async_refresh)
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
