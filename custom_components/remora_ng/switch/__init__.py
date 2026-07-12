"""Switch platform for remora_ng."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.remora_ng.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from homeassistant.components.switch import SwitchEntityDescription

from .example_switch import ENTITY_DESCRIPTIONS as SWITCH_DESCRIPTIONS, RemoraSwitch

if TYPE_CHECKING:
    from custom_components.remora_ng.data import RemoraConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Combine all entity descriptions from different modules
ENTITY_DESCRIPTIONS: tuple[SwitchEntityDescription, ...] = (*SWITCH_DESCRIPTIONS,)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        RemoraSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in SWITCH_DESCRIPTIONS
    )
