"""The Remora integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RemoraApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, PLATFORMS
from .coordinator import RemoraDataUpdateCoordinator
from .data import RemoraConfigEntry, RemoraData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> bool:
    """Set up Remora from a config entry."""

    session = async_get_clientsession(hass)

    api = RemoraApi(
        session=session,
        host=entry.data[CONF_HOST],
    )

    coordinator = RemoraDataUpdateCoordinator(
        hass,
        LOGGER,
        config_entry=entry,
        name=DOMAIN,
        # NOTE: adaptez si DEFAULT_SCAN_INTERVAL est déjà un timedelta
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    # runtime_data doit être défini AVANT le premier rafraîchissement,
    # car _async_update_data() y accède via self.config_entry.runtime_data.client
    entry.runtime_data = RemoraData(
        client=api,
        coordinator=coordinator,
    )

    # Premier rafraîchissement obligatoire
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
