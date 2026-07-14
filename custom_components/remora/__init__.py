"""The Remora integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from custom_components.remora.api import RemoraApi
from custom_components.remora.const import CONF_DEBUG, DEFAULT_DEBUG, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, PLATFORMS
from custom_components.remora.coordinator import RemoraDataUpdateCoordinator
from custom_components.remora.data import RemoraConfigEntry, RemoraData
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


def _apply_debug_mode(entry: RemoraConfigEntry) -> None:
    """Adjusts the integration log level according to the debug option.

    Deliberately simple approach (no `logger.set_level` service):
    the level is reapplied each time the entry is (re)loaded, so
    no need for any particular persistence. A restart of HA or a
    integration reload reapplies the current option.
    """

    debug_enabled = entry.options.get(CONF_DEBUG, DEFAULT_DEBUG)

    LOGGER.setLevel(logging.DEBUG if debug_enabled else logging.NOTSET)

    LOGGER.debug(
        "Mode debug %s pour l'entrée %s",
        "activé" if debug_enabled else "désactivé",
        entry.entry_id,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> bool:
    """Set up Remora from a config entry."""

    _apply_debug_mode(entry)

    session = async_get_clientsession(hass)

    api = RemoraApi(
        session=session,
        host=entry.data[CONF_HOST],
    )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = RemoraDataUpdateCoordinator(
        hass,
        LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_interval=timedelta(seconds=scan_interval),
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

    # Recharge l'intégration à chaque modification des options
    # (intervalle de rafraîchissement, mode debug) pour repartir sur une
    # configuration propre plutôt que de muter le coordinator en place.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> None:
    """Recharge l'entrée quand ses options changent."""

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
