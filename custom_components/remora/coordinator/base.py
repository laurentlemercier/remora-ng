"""Core DataUpdateCoordinator implementation for remora."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from remora.api import CannotConnect
from remora.api.models import RemoraState
from remora.const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from .data import RemoraConfigEntry


class RemoraDataUpdateCoordinator(DataUpdateCoordinator[RemoraState]):
    """Manage fetching data from the Remora API."""

    config_entry: RemoraConfigEntry

    device_info: DeviceInfo

    async def _async_setup(self) -> None:
        """Set up the coordinator."""

        client = self.config_entry.runtime_data.client

        try:
            device = await client.async_validate_connection()
        except CannotConnect as exception:
            raise UpdateFailed(
                translation_domain="remora",
                translation_key="update_failed",
            ) from exception

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, device.unique_id)},
            manufacturer=device.manufacturer,
            name=device.name,
            model=device.model,
            hw_version=device.hardware,
            sw_version=device.firmware,
            serial_number=device.unique_id,
            connections={("ip", client.host)},
            configuration_url=client.base_url,
        )

        LOGGER.debug(
            "Coordinator setup complete for %s",
            self.config_entry.entry_id,
        )

    async def _async_update_data(self) -> RemoraState:
        """Fetch data from the Remora device."""

        client = self.config_entry.runtime_data.client

        try:
            return await client.async_get_state()
        except CannotConnect as exception:
            LOGGER.exception("Error communicating with Remora")
            raise UpdateFailed(
                translation_domain="remora",
                translation_key="update_failed",
            ) from exception
