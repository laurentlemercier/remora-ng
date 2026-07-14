"""Models used by the Remora integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, StrEnum

#
# ------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------
#


class FilPiloteMode(StrEnum):
    """Pilot wire mode."""

    COMFORT = "C"
    ARRET = "A"
    ECO = "E"
    HORS_GEL = "H"
    DELESTAGE = "D"
    ECO1 = "1"
    ECO2 = "2"

    @property
    def label(self) -> str:
        """Return a human readable label."""

        return {
            FilPiloteMode.COMFORT: "Confort",  # codespell:ignore Confort
            FilPiloteMode.ARRET: "Arrêt",
            FilPiloteMode.ECO: "Eco",
            FilPiloteMode.HORS_GEL: "Hors Gel",
            FilPiloteMode.DELESTAGE: "Délestage",
            FilPiloteMode.ECO1: "Eco -1°C",
            FilPiloteMode.ECO2: "Eco -2°C",
        }[self]


class RelaisEtat(IntEnum):
    """Relay state."""

    OUVERT = 0
    FERME = 1


class RelaisMode(IntEnum):
    """Relay operating mode."""

    ARRET = 0
    MARCHE_FORCEE = 1
    AUTOMATIQUE = 2


#
# ------------------------------------------------------------------
# System information (raw system.json)
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class SystemInfo:
    """Raw system information, as returned by system.json.

    This is an intermediate parsing result. Its fields are extracted
    into `RemoraDevice`, including `free_ram`.
    """

    firmware: str
    hardware: str
    chip_id: str
    compiled: str
    sdk_version: str
    boot_version: str
    modules: str
    flash_real_size: int
    firmware_size: int
    free_size: int
    analog_mv: int
    spiffs_total: int
    spiffs_used: int
    spiffs_occupation: int
    free_ram: int


#
# ------------------------------------------------------------------
# Static information
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class RemoraDevice:
    """Static information about the device."""

    unique_id: str

    manufacturer: str = "Remora"

    name: str = "Remora"

    model: str = ""

    firmware: str = ""

    hardware: str = ""

    compiled: str = ""

    sdk_version: str = ""

    boot_version: str = ""

    modules: str = ""

    flash_real_size: int = 0

    firmware_size: int = 0

    free_size: int = 0

    analog_mv: int = 0

    spiffs_total: int = 0

    spiffs_used: int = 0

    spiffs_occupation: int = 0

    free_ram: int = 0


#
# ------------------------------------------------------------------
# Relay
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class RelaisStatus:
    """Relay status."""

    state: RelaisEtat

    mode: RelaisMode

    @property
    def is_closed(self) -> bool:
        """Return True if relay is closed."""

        return self.state is RelaisEtat.FERME


#
# ------------------------------------------------------------------
# Pilot wire
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class FilPiloteStatus:
    """Current pilot wire outputs.

    A Remora always exposes exactly 7 pilot wire outputs (fp1..fp7).
    """

    fp1: FilPiloteMode

    fp2: FilPiloteMode

    fp3: FilPiloteMode

    fp4: FilPiloteMode

    fp5: FilPiloteMode

    fp6: FilPiloteMode

    fp7: FilPiloteMode

    def __getitem__(
        self,
        index: int,
    ) -> FilPiloteMode:
        """Return pilot output using a 1-based index."""

        if not 1 <= index <= 7:
            raise IndexError(index)

        return getattr(self, f"fp{index}")

    def as_list(
        self,
    ) -> list[FilPiloteMode]:
        """Return outputs as a list."""

        return [
            self.fp1,
            self.fp2,
            self.fp3,
            self.fp4,
            self.fp5,
            self.fp6,
            self.fp7,
        ]

    @property
    def count(self) -> int:
        """Return number of pilot wire outputs (always 7)."""

        return len(self.as_list())


#
# ------------------------------------------------------------------
# Load shedding
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class DelestageStatus:
    """Load shedding."""

    enabled: bool

    state: str


#
# ------------------------------------------------------------------
# Teleinfo
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class Teleinfo:
    """Teleinfo values.

    The content depends on the enabled options
    of the Remora firmware.
    """

    raw: dict[str, str]


#
# ------------------------------------------------------------------
# Dynamic state
# ------------------------------------------------------------------
#


@dataclass(slots=True, frozen=True)
class RemoraState:
    """Dynamic Remora state."""

    device: RemoraDevice

    relais: RelaisStatus

    fil_pilote: FilPiloteStatus

    delestage: DelestageStatus

    uptime: timedelta

    teleinfo: Teleinfo | None = None

    @property
    def relay_closed(self) -> bool:
        """Return True if relay is closed."""

        return self.relais.is_closed

    @property
    def has_teleinfo(self) -> bool:
        """Return True if teleinfo is enabled."""

        return self.teleinfo is not None

    @property
    def pilot_count(self) -> int:
        """Return number of pilot wire outputs."""

        return self.fil_pilote.count
