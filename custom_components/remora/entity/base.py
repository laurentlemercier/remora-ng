"""Entity API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.remora.const import ATTRIBUTION
from custom_components.remora.coordinator import RemoraDataUpdateCoordinator
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity import EntityDescription


class RemoraEntity(CoordinatorEntity[RemoraDataUpdateCoordinator]):
    """Base entity class for remora."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        # Unique ID de l'entité basé sur l'entry_id et la clé du capteur
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity_description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Returns the device information from the coordinator."""
        return self.coordinator.device_info
