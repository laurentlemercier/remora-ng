"""The Remora integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RemoraApi
from .const import DOMAIN, LOGGER, PLATFORMS
from .coordinator import RemoraCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Remora from a config entry."""

    session = async_get_clientsession(hass)

    api = RemoraApi(
        session=session,
        host=entry.data[CONF_HOST],
    )

    coordinator = RemoraCoordinator(
        hass=hass,
        api=api,
        logger=LOGGER,
    )

    # Premier rafraîchissement obligatoire
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
