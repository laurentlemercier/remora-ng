"""Sensor platform for remora."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfElectricPotential, UnitOfInformation
import homeassistant.util.dt as dt_util
from remora.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from remora.entity import RemoraEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import RemoraDataUpdateCoordinator
    from .data import RemoraConfigEntry
    from .models import RemoraState

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RemoraSensorEntityDescription(SensorEntityDescription):
    """Décrit un capteur Remora et où lire sa valeur dans RemoraState."""

    value_fn: Callable[[RemoraState], str | int | float | datetime | None]


# A diagnostic sensor per field from SystemInfo. `free_ram` lives at the root
# of RemoraState (dynamic data on the model side) but remains attached here
# functionally to system information, like the rest of this group.

SYSTEM_SENSORS: tuple[RemoraSensorEntityDescription, ...] = (
    RemoraSensorEntityDescription(
        key="firmware",
        name="Version du firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Redondant avec device_info.sw_version, désactivé par défaut.
        entity_registry_enabled_default=False,
        value_fn=lambda state: state.device.firmware,
    ),
    RemoraSensorEntityDescription(
        key="hardware",
        name="Version du matériel",
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Redondant avec device_info.hw_version, désactivé par défaut.
        entity_registry_enabled_default=False,
        value_fn=lambda state: state.device.hardware,
    ),
    RemoraSensorEntityDescription(
        key="chip_id",
        name="Identifiant de la puce",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        # Redondant avec device_info.serial_number, désactivé par défaut.
        entity_registry_enabled_default=False,
        value_fn=lambda state: state.device.unique_id,
    ),
    RemoraSensorEntityDescription(
        key="compiled",
        name="Date de compilation",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.compiled,
    ),
    RemoraSensorEntityDescription(
        key="sdk_version",
        name="Version du SDK",
        icon="mdi:code-braces",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.sdk_version,
    ),
    RemoraSensorEntityDescription(
        key="boot_version",
        name="Version du bootloader",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.boot_version,
    ),
    RemoraSensorEntityDescription(
        key="modules",
        name="Modules activés",
        icon="mdi:puzzle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.modules,
    ),
    RemoraSensorEntityDescription(
        key="flash_real_size",
        name="Taille de la flash",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.flash_real_size,
    ),
    RemoraSensorEntityDescription(
        key="firmware_size",
        name="Taille du firmware",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.firmware_size,
    ),
    RemoraSensorEntityDescription(
        key="free_size",
        name="Espace flash libre",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.free_size,
    ),
    RemoraSensorEntityDescription(
        key="analog_mv",
        name="Entrée analogique",
        icon="mdi:flash",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.analog_mv,
    ),
    RemoraSensorEntityDescription(
        key="spiffs_total",
        name="Espace SPIFFS total",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.KILOBYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.spiffs_total,
    ),
    RemoraSensorEntityDescription(
        key="spiffs_used",
        name="Espace SPIFFS utilisé",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.KILOBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.spiffs_used,
    ),
    RemoraSensorEntityDescription(
        key="spiffs_occupation",
        name="Occupation SPIFFS",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.device.spiffs_occupation,
    ),
    RemoraSensorEntityDescription(
        key="free_ram",
        name="Mémoire RAM libre",
        icon="mdi:memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.KILOBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        # `free_ram` vit sur RemoraDevice, pas directement sur RemoraState.
        value_fn=lambda state: state.device.free_ram,
    ),
)


def _last_boot(state: RemoraState) -> datetime:
    """Retourne l'horodatage approximatif du dernier démarrage.

    Arrondi à la minute pour éviter de générer un nouvel état à chaque
    cycle de rafraîchissement à cause de la légère latence réseau lors
    de la lecture de l'uptime.
    """

    boot = dt_util.utcnow() - state.uptime

    return boot.replace(second=0, microsecond=0)


# Sensors based on dynamic data (not SystemInfo), but which
# remain diagnostic information.

DYNAMIC_SENSORS: tuple[RemoraSensorEntityDescription, ...] = (
    RemoraSensorEntityDescription(
        key="last_boot",
        name="Dernier démarrage",
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_last_boot,
    ),
)


class RemoraSystemSensor(RemoraEntity, SensorEntity):
    """Capteur générique pour le système Remora."""

    entity_description: RemoraSensorEntityDescription

    def __init__(
        self,
        coordinator: RemoraDataUpdateCoordinator,
        description: RemoraSensorEntityDescription,
    ) -> None:
        """Initialise le capteur basé sur sa description."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> str | int | float | datetime | None:
        """Retourne la valeur du capteur dynamiquement depuis le coordinateur."""
        data = self.coordinator.data

        if data is None:
            _LOGGER.debug(
                "Aucune donnée disponible pour %s",
                self.entity_description.key,
            )
            return None

        return self.entity_description.value_fn(data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RemoraConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

    # Nous passons uniquement le coordinateur à l'entité.
    # L'entité extrait d'elle-même les infos de l'appareil via `coordinator.device_info`
    entities = [RemoraSystemSensor(coordinator, description) for description in (*SYSTEM_SENSORS, *DYNAMIC_SENSORS)]

    async_add_entities(entities)
