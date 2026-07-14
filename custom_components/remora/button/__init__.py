"""Button platform for remora."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from custom_components.remora.entity import RemoraEntity
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory

if TYPE_CHECKING:
    from custom_components.remora.coordinator import RemoraDataUpdateCoordinator
    from custom_components.remora.data import RemoraConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

# Requis en dur (littéral) par hassfest, ne pas remplacer par un import.
PARALLEL_UPDATES = 1

RESTART_DESCRIPTION = ButtonEntityDescription(
    key="restart",
    name="Redémarrer",
    device_class=ButtonDeviceClass.RESTART,
    entity_category=EntityCategory.CONFIG,
)


class RemoraRestartButton(RemoraEntity, ButtonEntity):
    """Bouton pour redémarrer le Remora."""

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
    ) -> None:
        """Initialise le bouton."""
        super().__init__(coordinator, RESTART_DESCRIPTION)

    async def async_press(self) -> None:
        """Envoie la commande de redémarrage à l'appareil."""
        client = self.coordinator.config_entry.runtime_data.client

        _LOGGER.info("Redémarrage demandé pour %s", client.host)

        # `async_restart` already swallows connection/timeout errors
        # on the API side, since the device cuts off the connection as soon as it
        # restarts: nothing to catch here.
        await client.async_restart()

        # No immediate refresh: the device will be unreachable for
        # its restart. The coordinator’s next polling cycle
        # will return to normal once it is restarted.


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities([RemoraRestartButton(coordinator)])
