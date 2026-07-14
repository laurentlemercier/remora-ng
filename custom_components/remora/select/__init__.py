"""Select platform for remora."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.exceptions import HomeAssistantError
from remora.api import CannotConnect, RemoraCommandError
from remora.api.models import FilPiloteMode
from remora.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from remora.entity import RemoraEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import RemoraDataUpdateCoordinator
    from .data import RemoraConfigEntry

_LOGGER = logging.getLogger(__name__)

# Modes actually implemented on the integration side. Remora firmware
# also supports Load Shedding, Eco -1°C, and Eco -2°C, but they are not
# managed here: so we don’t offer them in the list of options.

SUPPORTED_MODES: tuple[FilPiloteMode, ...] = (
    FilPiloteMode.ARRET,
    FilPiloteMode.COMFORT,
    FilPiloteMode.ECO,
    FilPiloteMode.HORS_GEL,
)

# Options displayed in the select, in the order above.
_OPTIONS: tuple[str, ...] = tuple(mode.label for mode in SUPPORTED_MODES)

# Matching label displayed -> enumeration member, for the order.
_LABEL_TO_MODE: dict[str, FilPiloteMode] = {mode.label: mode for mode in SUPPORTED_MODES}


@dataclass(frozen=True, kw_only=True)
class RemoraFilPiloteSelectEntityDescription(SelectEntityDescription):
    """Décrit un select de sortie fil pilote Remora."""

    fp_index: int


FP_SELECTS: tuple[RemoraFilPiloteSelectEntityDescription, ...] = tuple(
    RemoraFilPiloteSelectEntityDescription(
        key=f"fp{index}",
        name=f"Fil pilote {index}",
        icon="mdi:radiator",
        options=list(_OPTIONS),
        fp_index=index,
    )
    for index in range(1, 8)
)


class RemoraFilPiloteSelect(RemoraEntity, SelectEntity):
    """Select pour une sortie fil pilote Remora."""

    entity_description: RemoraFilPiloteSelectEntityDescription

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
        description: RemoraFilPiloteSelectEntityDescription,
    ) -> None:
        """Initialise le select."""
        super().__init__(coordinator, description)

    def _raw_mode(self) -> FilPiloteMode | None:
        """Retourne le mode brut rapporté par l'appareil, sans filtrage."""
        data = self.coordinator.data

        if data is None:
            return None

        return data.fil_pilote[self.entity_description.fp_index]

    @property
    def current_option(self) -> str | None:
        """Retourne le mode actuellement actif pour cette sortie."""
        mode = self._raw_mode()

        if mode is None:
            return None

        if mode not in SUPPORTED_MODES:
            # Options displayed in the select, in the above order # Ex. the box itself applies automatic load shedding.
            # We can’t represent this value in the options
            # exposed, so the entity changes to "unknown" rather than
            # to return an invalid option.
            _LOGGER.debug(
                "Mode %s non supporté pour %s, état inconnu",
                mode,
                self.entity_description.key,
            )
            return None

        return mode.label

    @property
    def icon(self) -> str | None:
        """Icône spécifique quand le mode réel n'est pas déterminable."""
        mode = self._raw_mode()

        if mode is not None and mode not in SUPPORTED_MODES:
            return "mdi:help-circle-outline"

        return self.entity_description.icon

    async def async_select_option(self, option: str) -> None:
        """Change le mode de la sortie fil pilote."""
        mode = _LABEL_TO_MODE.get(option)

        if mode is None:
            # Ne devrait pas arriver : `option` provient forcément de la
            # liste `options` déclarée sur l'entité.
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="invalid_fil_pilote_mode",
                translation_placeholders={"option": option},
            )

        client = self.coordinator.config_entry.runtime_data.client

        try:
            await client.async_set_fil_pilote(self.entity_description.fp_index, mode)
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
    """Set up the select platform."""
    coordinator = entry.runtime_data.coordinator

    entities = [RemoraFilPiloteSelect(coordinator, description) for description in FP_SELECTS]

    async_add_entities(entities)
