"""Constants for the Remora integration."""

from logging import Logger, getLogger

from homeassistant.const import Platform

DOMAIN = "remora"
MANUFACTURER = "Remora"

LOGGER: Logger = getLogger(__package__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.CLIMATE,
    Platform.BUTTON,
]

DEFAULT_SCAN_INTERVAL = 30  # secondes
MIN_SCAN_INTERVAL = 5  # secondes (entier, pas timedelta)
MAX_SCAN_INTERVAL = 3600  # secondes (entier, pas timedelta)

CONF_DEBUG = "debug"
DEFAULT_DEBUG = False

CONF_ENABLE_CLIMATE = "enable_climate"
DEFAULT_ENABLE_CLIMATE = True

CONF_ENABLE_SELECT = "enable_select"
DEFAULT_ENABLE_SELECT = False

PARALLEL_UPDATES = 1
ATTRIBUTION = "Data provided by Remora"
