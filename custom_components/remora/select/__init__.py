"""Select platform for remora."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from custom_components.remora.api import CannotConnect, RemoraCommandError
from custom_components.remora.api.models import FilPiloteMode
from custom_components.remora.const import (
    CONF_ENABLE_SELECT,
    DEFAULT_ENABLE_SELECT,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.remora.entity import RemoraEntity
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import RemoraDataUpdateCoordinator
    from .data import RemoraConfigEntry

_LOGGER = logging.getLogger(__name__)

# Modes actually implemented by this integration. The Remora firmware
# also supports Load Shedding, Eco -1°C and Eco -2°C, but they are not
# exposed here, so they are not offered as options.

SUPPORTED_MODES: tuple[FilPiloteMode, ...] = (
    FilPiloteMode.ARRET,
    FilPiloteMode.COMFORT,
    FilPiloteMode.ECO,
    FilPiloteMode.HORS_GEL,
)

# Options displayed in the select, in order.
_OPTIONS: tuple[str, ...] = tuple(mode.label for mode in SUPPORTED_MODES)

# Map of displayed label to FilPiloteMode.
_LABEL_TO_MODE: dict[str, FilPiloteMode] = {mode.label: mode for mode in SUPPORTED_MODES}


@dataclass(frozen=True, kw_only=True)
class RemoraFilPiloteSelectEntityDescription(SelectEntityDescription):
    """Describe a Remora pilot wire select output."""

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
    """Select entity for a Remora pilot wire output."""

    entity_description: RemoraFilPiloteSelectEntityDescription

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
        description: RemoraFilPiloteSelectEntityDescription,
        *,
        enabled_default: bool,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, description)
        # HA only applies this value when the entity is first created in the
        # registry; changing it does not affect existing entities.
        self._attr_entity_registry_enabled_default = enabled_default

    def _raw_mode(self) -> FilPiloteMode | None:
        """Return the raw mode reported by the device without filtering."""
        data = self.coordinator.data

        if data is None:
            return None

        return data.fil_pilote[self.entity_description.fp_index]

    @property
    def current_option(self) -> str | None:
        """Return the currently active mode for this output."""
        mode = self._raw_mode()

        if mode is None:
            return None

        if mode not in SUPPORTED_MODES:
            _LOGGER.debug(
                "Mode %s not supported for %s, showing unknown state",
                mode,
                self.entity_description.key,
            )
            return None

        return mode.label

    @property
    def icon(self) -> str | None:
        """Return a specific icon when the actual mode cannot be determined."""
        mode = self._raw_mode()

        if mode is not None and mode not in SUPPORTED_MODES:
            return "mdi:help-circle-outline"

        return self.entity_description.icon

    async def async_select_option(self, option: str) -> None:
        """Change the pilot wire mode."""
        mode = _LABEL_TO_MODE.get(option)

        if mode is None:
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
                "Command rejected for %s: %s",
                self.entity_description.key,
                exception,
            )
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="command_failed",
            ) from exception
        except CannotConnect as exception:
            _LOGGER.error(
                "Unable to reach Remora for %s: %s",
                self.entity_description.key,
                exception,
            )
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="update_failed",
            ) from exception

        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator = entry.runtime_data.coordinator
    enabled_default = entry.options.get(CONF_ENABLE_SELECT, DEFAULT_ENABLE_SELECT)

    entities = [
        RemoraFilPiloteSelect(coordinator, description, enabled_default=enabled_default) for description in FP_SELECTS
    ]

    async_add_entities(entities)
