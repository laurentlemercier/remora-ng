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
]

# DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
# MIN_SCAN_INTERVAL = timedelta(seconds=5)
# MAX_SCAN_INTERVAL = timedelta(seconds=3600)

DEFAULT_SCAN_INTERVAL = 30  # secondes
MIN_SCAN_INTERVAL = 5  # secondes (entier, pas timedelta)
MAX_SCAN_INTERVAL = 3600  # secondes (entier, pas timedelta)

PARALLEL_UPDATES = 1
ATTRIBUTION = "Data provided by Remora"
