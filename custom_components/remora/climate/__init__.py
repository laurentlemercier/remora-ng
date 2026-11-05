"""Climate platform for remora."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING

from custom_components.remora.api import CannotConnect, RemoraCommandError
from custom_components.remora.api.models import FilPiloteMode
from custom_components.remora.const import (
    CONF_ENABLE_CLIMATE,
    DEFAULT_ENABLE_CLIMATE,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.remora.entity import RemoraEntity
from homeassistant.components.climate import ClimateEntity, ClimateEntityDescription
from homeassistant.components.climate.const import PRESET_COMFORT, PRESET_ECO, ClimateEntityFeature, HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.remora.coordinator import RemoraDataUpdateCoordinator
    from custom_components.remora.data import RemoraConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

# Only the four modes already managed by the select platform are exposed.
# The firmware also supports Load Shedding, Eco -1°C, and Eco -2°C, but
# they are not offered here. A mode reported outside this set is simply
# shown as an unknown preset rather than as an invalid option.

# Home Assistant has no built-in "frost" preset. Use an explicit French
# label so the Hors Gel mode is readable in the climate card.
PRESET_HORS_GEL = "hors_gel"

_PRESET_TO_MODE: dict[str, FilPiloteMode] = {
    PRESET_COMFORT: FilPiloteMode.COMFORT,
    PRESET_ECO: FilPiloteMode.ECO,
    PRESET_HORS_GEL: FilPiloteMode.HORS_GEL,
}

_MODE_TO_PRESET: dict[FilPiloteMode, str] = {mode: preset for preset, mode in _PRESET_TO_MODE.items()}


@dataclass(frozen=True, kw_only=True)
class RemoraFilPiloteClimateEntityDescription(ClimateEntityDescription):
    """Describe a Remora pilot wire climate entity."""

    fp_index: int


FP_CLIMATES: tuple[RemoraFilPiloteClimateEntityDescription, ...] = tuple(
    RemoraFilPiloteClimateEntityDescription(
        key=f"fp{index}_climate",
        name=f"Fil pilote {index}",
        icon="mdi:radiator",
        fp_index=index,
    )
    for index in range(1, 8)
)


class RemoraFilPiloteClimate(RemoraEntity, ClimateEntity):
    """Climate entity for a Remora pilot wire output.

    The pilot wire has no temperature setpoint; this entity only controls
    the heating mode (HVAC mode and preset).
    """

    entity_description: RemoraFilPiloteClimateEntityDescription

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_preset_modes = list(_PRESET_TO_MODE)
    _attr_supported_features = ClimateEntityFeature.PRESET_MODE
    # HA reads `temperature_unit` in `capability_attributes` even if no
    # temperature is managed, so this attribute must be set.
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
        description: RemoraFilPiloteClimateEntityDescription,
        *,
        enabled_default: bool,
    ) -> None:
        """Initialize the climate entity."""
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
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        mode = self._raw_mode()

        if mode is None:
            return None

        if mode is FilPiloteMode.ARRET:
            return HVACMode.OFF

        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset, or None if not representable."""
        mode = self._raw_mode()

        if mode is None or mode is FilPiloteMode.ARRET:
            return None

        preset = _MODE_TO_PRESET.get(mode)

        if preset is None:
            _LOGGER.debug(
                "Mode %s not supported for %s, preset unknown",
                mode,
                self.entity_description.key,
            )

        return preset

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode for the pilot wire output."""
        if hvac_mode is HVACMode.OFF:
            mode = FilPiloteMode.ARRET
        elif hvac_mode is HVACMode.HEAT:
            current = self._raw_mode()
            # Keep the current preset if representable, otherwise fall back
            # to Comfort.
            if current is not None and current in _MODE_TO_PRESET:
                mode = current
            else:
                mode = FilPiloteMode.COMFORT
        else:
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="invalid_hvac_mode",
                translation_placeholders={"mode": hvac_mode},
            )

        await self._async_apply_mode(mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset for the pilot wire output."""
        mode = _PRESET_TO_MODE.get(preset_mode)

        if mode is None:
            raise HomeAssistantError(
                translation_domain="remora",
                translation_key="invalid_fil_pilote_mode",
                translation_placeholders={"option": preset_mode},
            )

        await self._async_apply_mode(mode)

    async def _async_apply_mode(self, mode: FilPiloteMode) -> None:
        """Send the mode to the device and refresh state."""
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
    """Set up the climate platform."""
    coordinator = entry.runtime_data.coordinator
    enabled_default = entry.options.get(CONF_ENABLE_CLIMATE, DEFAULT_ENABLE_CLIMATE)

    entities = [
        RemoraFilPiloteClimate(coordinator, description, enabled_default=enabled_default) for description in FP_CLIMATES
    ]

    async_add_entities(entities)
