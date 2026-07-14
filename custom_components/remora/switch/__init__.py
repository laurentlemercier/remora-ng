"""Switch platform for remora."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from custom_components.remora.api import CannotConnect, RemoraCommandError
from custom_components.remora.api.models import RelaisEtat, RelaisMode
from custom_components.remora.entity import RemoraEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.remora.api import RemoraApi
    from custom_components.remora.api.models import RemoraState
    from custom_components.remora.coordinator import RemoraDataUpdateCoordinator
    from custom_components.remora.data import RemoraConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

# Requis en dur (littéral) par hassfest, ne pas remplacer par un import.
PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class RemoraSwitchEntityDescription(SwitchEntityDescription):
    """Décrit un switch Remora : lecture d'état + actions on/off."""

    is_on_fn: Callable[[RemoraState], bool]
    turn_on_fn: Callable[[RemoraApi], Awaitable[None]]
    turn_off_fn: Callable[[RemoraApi], Awaitable[None]]


SWITCHES: tuple[RemoraSwitchEntityDescription, ...] = (
    RemoraSwitchEntityDescription(
        key="relais",
        name="Relais",
        icon="mdi:electric-switch",
        is_on_fn=lambda state: state.relais.is_closed,
        turn_on_fn=lambda client: client.async_set_relais(RelaisEtat.FERME),
        turn_off_fn=lambda client: client.async_set_relais(RelaisEtat.OUVERT),
    ),
    RemoraSwitchEntityDescription(
        key="marche_forcee",
        name="Marche forcée",
        icon="mdi:hand-back-right",
        is_on_fn=lambda state: state.relais.mode is RelaisMode.MARCHE_FORCEE,
        turn_on_fn=lambda client: client.async_set_relais_mode(RelaisMode.MARCHE_FORCEE),
        # Désactiver la marche forcée repasse le relais en mode automatique.
        turn_off_fn=lambda client: client.async_set_relais_mode(RelaisMode.AUTOMATIQUE),
    ),
)


class RemoraSwitch(RemoraEntity, SwitchEntity):
    """Switch générique pour le relais Remora."""

    entity_description: RemoraSwitchEntityDescription

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
        description: RemoraSwitchEntityDescription,
    ) -> None:
        """Initialise le switch."""
        super().__init__(coordinator, description)

    @property
    def is_on(self) -> bool | None:
        """Retourne l'état actuel du switch."""
        data = self.coordinator.data

        if data is None:
            return None

        return self.entity_description.is_on_fn(data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Active le switch."""
        await self._async_send_command(self.entity_description.turn_on_fn)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Désactive le switch."""
        await self._async_send_command(self.entity_description.turn_off_fn)

    async def _async_send_command(
        self,
        command: Callable[[RemoraApi], Awaitable[None]],
    ) -> None:
        """Envoie une commande à l'appareil puis rafraîchit l'état."""
        client = self.coordinator.config_entry.runtime_data.client

        try:
            await command(client)
        except RemoraCommandError as exception:
            _LOGGER.error(
                "Commande refusée pour %s: %s",
                self.entity_description.key,
                exception,
            )
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="command_failed",
            ) from exception
        except CannotConnect as exception:
            _LOGGER.error(
                "Impossible de joindre Remora pour %s: %s",
                self.entity_description.key,
                exception,
            )
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="update_failed",
            ) from exception

        # On force une actualisation immédiate plutôt que d'attendre le
        # prochain cycle du coordinator, pour refléter l'état réel de suite.
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = entry.runtime_data.coordinator

    entities = [RemoraSwitch(coordinator, description) for description in SWITCHES]

    async_add_entities(entities)
