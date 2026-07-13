"""
Core DataUpdateCoordinator implementation for remora.

This module contains the main coordinator class that manages data fetching
and updates for all entities in the integration.

For more information on coordinators:
https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.remora.const import LOGGER
from custom_components.remora.remora import CannotConnect
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from custom_components.remora.data import RemoraConfigEntry


class RemoraDataUpdateCoordinator(DataUpdateCoordinator):
    """
    Class to manage fetching data from the API.

    Le client API (RemoraApi) et le coordinator lui-même sont accessibles
    via config_entry.runtime_data (voir data.py), pas via des attributes
    passés au constructeur : le coordinator est instancié avec la
    signature standard de DataUpdateCoordinator (hass, logger,
    config_entry, name, update_interval) dans __init__.py.

    Attributes:
        config_entry: The config entry for this integration instance.
    """

    config_entry: RemoraConfigEntry

    async def _async_setup(self) -> None:
        """
        Set up the coordinator.

        Appelé automatiquement par async_config_entry_first_refresh(),
        avant la première récupération de données.
        """
        LOGGER.debug("Coordinator setup complete for %s", self.config_entry.entry_id)

    async def _async_update_data(self) -> Any:
        """
        Fetch data from the Remora device.

        Returns:
            dict: les données agrégées (system, relais, fp, teleinfo).

        Raises:
            UpdateFailed: si la communication avec le boîtier échoue.
        """
        try:
            return await self.config_entry.runtime_data.client.async_get_all_data()
        except CannotConnect as exception:
            LOGGER.exception("Error communicating with Remora")
            raise UpdateFailed(
                translation_domain="remora",
                translation_key="update_failed",
            ) from exception
