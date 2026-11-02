"""The Remora integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from custom_components.remora.api import RemoraApi
from custom_components.remora.const import (
    CONF_DEBUG,
    CONF_ENABLE_CLIMATE,
    CONF_ENABLE_SELECT,
    DEFAULT_DEBUG,
    DEFAULT_ENABLE_CLIMATE,
    DEFAULT_ENABLE_SELECT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    PLATFORMS,
)
from custom_components.remora.coordinator import RemoraDataUpdateCoordinator
from custom_components.remora.data import RemoraConfigEntry, RemoraData
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
        "Debug mode %s for entry %s",
        "enabled" if debug_enabled else "disabled",
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

    # runtime_data must be defined before the first refresh so
    # _async_update_data() can access it via self.config_entry.runtime_data.client
    entry.runtime_data = RemoraData(
        client=api,
        coordinator=coordinator,
    )

    # First refresh is required
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    # Update entity registry when enable/disable options change
    await _async_update_entity_registry(hass, entry)

    # Reload the integration on any options change (refresh interval,
    # debug mode, enabled entities) to apply cleanly instead of mutating
    # the coordinator in place.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_entity_registry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> None:
    """Enable/disable climate and select entities based on options."""
    entity_reg = er.async_get(hass)
    enable_climate = entry.options.get(CONF_ENABLE_CLIMATE, DEFAULT_ENABLE_CLIMATE)
    enable_select = entry.options.get(CONF_ENABLE_SELECT, DEFAULT_ENABLE_SELECT)

    for entity in list(entity_reg.entities.values()):
        if entity.config_entry_id != entry.entry_id:
            continue
        entity_id = entity.entity_id
        if entity.domain == "climate" and ("fil_pilote" in entity_id or "_fp" in entity_id):
            if enable_climate:
                entity_reg.async_update_entity(entity_id, disabled_by=None)
            else:
                entity_reg.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
        elif entity.domain == "select" and ("fil_pilote" in entity_id or "_fp" in entity_id):
            if enable_select:
                entity_reg.async_update_entity(entity_id, disabled_by=None)
            else:
                entity_reg.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)


async def _async_update_listener(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
) -> None:
    """Reload the entry when options change."""
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
