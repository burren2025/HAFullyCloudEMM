"""The Fully Cloud EMM integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FullyCloudClient
from .const import CONF_API_EMAIL, CONF_API_KEY, DOMAIN, PLATFORMS
from .coordinator import FullyCloudCoordinator

type FullyCloudConfigEntry = ConfigEntry[FullyCloudCoordinator]


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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FullyCloudConfigEntry
) -> bool:
    """Unload Fully Cloud EMM."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

