"""Constants for the Remora integration."""

from datetime import timedelta
from logging import Logger, getLogger

from homeassistant.const import Platform

DOMAIN = "remora"

LOGGER: Logger = getLogger(__package__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

MANUFACTURER = "Remora"

CONF_DEBUG = "debug"

DEFAULT_DEBUG = False
