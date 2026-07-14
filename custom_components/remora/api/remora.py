"""HTTP client for Remora."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import timedelta
import logging
import re
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .models import (
    DelestageStatus,
    FilPiloteMode,
    FilPiloteStatus,
    RelaisEtat,
    RelaisMode,
    RelaisStatus,
    RemoraDevice,
    RemoraState,
    SystemInfo,
    Teleinfo,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=5)


class CannotConnect(Exception):
    """Unable to communicate with Remora."""


class RemoraCommandError(Exception):
    """Command rejected by Remora."""


class InvalidResponse(Exception):
    """Unexpected response from Remora."""


class RemoraApi:
    """HTTP client for Remora."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
    ) -> None:
        """Initialize the client."""

        self._session = session
        self._host = host
        self._base_url = f"http://{host}"

        _LOGGER.debug("Initializing Remora API (%s)", host)

    @property
    def host(self) -> str:
        """Return configured host."""
        return self._host

    @property
    def base_url(self) -> str:
        """Return the base URL used to reach the device."""
        return self._base_url

    #
    # ---------------------------------------------------------
    # HTTP
    # ---------------------------------------------------------
    #

    async def _get_json(
        self,
        endpoint: str,
        *,
        optional: bool = False,
    ) -> Any:
        """Perform a GET request.

        If `optional` is True, a 404 response returns None instead
        of raising, while other errors still raise as usual.
        """

        url = f"{self._base_url}/{endpoint}"

        _LOGGER.debug("GET %s", url)

        try:
            async with self._session.get(
                url,
                timeout=_TIMEOUT,
            ) as response:
                if optional and response.status == 404:
                    _LOGGER.debug(
                        "GET %s -> 404 (optional endpoint)",
                        endpoint,
                    )
                    return None

                response.raise_for_status()

                data = await response.json(content_type=None)

                _LOGGER.debug(
                    "GET %s -> %s",
                    endpoint,
                    response.status,
                )

                return data

        except TimeoutError as err:
            _LOGGER.warning("Timeout requesting %s", endpoint)
            raise CannotConnect from err

        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "Communication error requesting %s: %s",
                endpoint,
                err,
            )
            raise CannotConnect from err

    async def _command(
        self,
        **params: Any,
    ) -> None:
        """Send a command."""

        query = urlencode(params)

        result = await self._get_json(f"?{query}")

        if result.get("response") != 0:
            _LOGGER.error(
                "Command rejected (%s)",
                result,
            )
            raise RemoraCommandError(result)

        _LOGGER.debug("Command accepted")

    #
    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    #

    @staticmethod
    def _parse_bytes(value: str) -> int:
        """Convert '4.00 MB' into bytes."""

        match = re.match(r"([\d.]+)\s*(KB|MB|B)", value)

        if match is None:
            raise InvalidResponse(value)

        number = float(match.group(1))
        unit = match.group(2)

        factor = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 * 1024,
        }[unit]

        return int(number * factor)

    @staticmethod
    def _parse_percent(value: str) -> int:
        """Convert '17%' into 17."""

        return int(value.rstrip("%"))

    @staticmethod
    def _parse_mv(value: str) -> int:
        """Convert '25 mV' into 25."""

        return int(value.replace("mV", "").strip())

    @staticmethod
    def _system_to_dict(
        data: list[dict[str, str]],
    ) -> dict[str, str]:
        """Convert Remora system.json into a dictionary."""

        return {item["na"]: item["va"] for item in data}

    #
    # ---------------------------------------------------------
    # Parsers
    # ---------------------------------------------------------
    #

    def _parse_system(
        self,
        raw: dict[str, str],
    ) -> SystemInfo:
        """Parse system.json."""

        return SystemInfo(
            firmware=raw["Version Logiciel"],
            hardware=raw["Version Matériel"],
            chip_id=raw["Chip ID"],
            compiled=raw["Compilé le"],
            sdk_version=raw["SDK Version"],
            boot_version=raw["Boot Version"],
            modules=raw["Modules activés"],
            flash_real_size=self._parse_bytes(raw["Flash Real Size"]),
            firmware_size=self._parse_bytes(raw["Firmware Size"]),
            free_size=self._parse_bytes(raw["Free Size"]),
            analog_mv=self._parse_mv(raw["Analog"]),
            spiffs_total=self._parse_bytes(raw["SPIFFS Total"]),
            spiffs_used=self._parse_bytes(raw["SPIFFS Used"]),
            spiffs_occupation=self._parse_percent(raw["SPIFFS Occupation"]),
            free_ram=self._parse_bytes(raw["Free Ram"]),
        )

    @staticmethod
    def _parse_device(
        system: SystemInfo,
    ) -> RemoraDevice:
        """Build the static Remora device information."""

        return RemoraDevice(
            unique_id=system.chip_id,
            manufacturer="Remora",
            name="Remora",
            model=system.hardware,
            firmware=system.firmware,
            hardware=system.hardware,
            compiled=system.compiled,
            sdk_version=system.sdk_version,
            boot_version=system.boot_version,
            modules=system.modules,
            flash_real_size=system.flash_real_size,
            firmware_size=system.firmware_size,
            free_size=system.free_size,
            analog_mv=system.analog_mv,
            spiffs_total=system.spiffs_total,
            spiffs_used=system.spiffs_used,
            spiffs_occupation=system.spiffs_occupation,
            free_ram=system.free_ram,
        )

    @staticmethod
    def _parse_relais(
        raw: dict[str, Any],
    ) -> RelaisStatus:
        """Parse relay."""

        return RelaisStatus(
            state=RelaisEtat(raw["relais"]),
            mode=RelaisMode(raw["fnct_relais"]),
        )

    @staticmethod
    def _parse_fp(
        raw: dict[str, str],
    ) -> FilPiloteStatus:
        """Parse pilot wire outputs."""

        return FilPiloteStatus(
            fp1=FilPiloteMode(raw["fp1"]),
            fp2=FilPiloteMode(raw["fp2"]),
            fp3=FilPiloteMode(raw["fp3"]),
            fp4=FilPiloteMode(raw["fp4"]),
            fp5=FilPiloteMode(raw["fp5"]),
            fp6=FilPiloteMode(raw["fp6"]),
            fp7=FilPiloteMode(raw["fp7"]),
        )

    @staticmethod
    def _parse_delestage(
        raw: dict[str, str],
    ) -> DelestageStatus:
        """Parse load shedding."""

        state = raw["etat"]

        return DelestageStatus(
            enabled=state.lower() != "désactivé",
            state=state,
        )

    #
    # ---------------------------------------------------------
    # State
    # ---------------------------------------------------------
    #

    async def _async_get_system(self) -> SystemInfo:
        """Return system information."""

        raw = await self._get_json("system.json")

        return self._parse_system(
            self._system_to_dict(raw),
        )

    async def _async_get_relais(self) -> RelaisStatus:
        """Return relay status."""

        raw = await self._get_json("relais")

        return self._parse_relais(raw)

    async def _async_get_fp(self) -> FilPiloteStatus:
        """Return pilot wire status."""

        raw = await self._get_json("fp")

        return self._parse_fp(raw)

    async def _async_get_delestage(
        self,
    ) -> DelestageStatus:
        """Return load shedding."""

        raw = await self._get_json("delestage")

        return self._parse_delestage(raw)

    async def _async_get_uptime(self) -> timedelta:
        """Return uptime."""

        raw = await self._get_json("uptime")

        return timedelta(
            seconds=int(raw["uptime"]),
        )

    async def _async_get_teleinfo(
        self,
    ) -> Teleinfo | None:
        """Return teleinfo, or None if the feature is not enabled."""

        raw = await self._get_json("tinfo", optional=True)

        if raw is None:
            _LOGGER.debug("Teleinfo not available")
            return None

        return Teleinfo(raw=raw)

    async def async_get_state(
        self,
    ) -> RemoraState:
        """Return complete Remora state."""

        _LOGGER.debug("Refreshing Remora state")

        (
            system,
            relais,
            fp,
            delestage,
            uptime,
            teleinfo,
        ) = await asyncio.gather(
            self._async_get_system(),
            self._async_get_relais(),
            self._async_get_fp(),
            self._async_get_delestage(),
            self._async_get_uptime(),
            self._async_get_teleinfo(),
        )

        state = RemoraState(
            device=self._parse_device(system),
            relais=relais,
            fil_pilote=fp,
            delestage=delestage,
            uptime=uptime,
            teleinfo=teleinfo,
        )

        _LOGGER.debug("Refresh completed")

        return state

    #
    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------
    #

    async def async_validate_connection(self) -> RemoraDevice:
        """Validate that the host is a Remora."""

        system = await self._async_get_system()

        device = self._parse_device(system)

        _LOGGER.info(
            "Connected to %s (%s)",
            device.model,
            device.firmware,
        )

        return device

    #
    # ---------------------------------------------------------
    # Commands
    # ---------------------------------------------------------
    #

    async def async_set_relais(
        self,
        state: RelaisEtat,
    ) -> None:
        """Set relay state."""

        _LOGGER.debug(
            "Setting relay state to %s",
            state.name,
        )

        await self._command(
            relais=state.value,
        )

    async def async_set_relais_mode(
        self,
        mode: RelaisMode,
    ) -> None:
        """Set relay mode."""

        _LOGGER.debug(
            "Setting relay mode to %s",
            mode.name,
        )

        await self._command(
            frelais=mode.value,
        )

    async def async_set_fil_pilote(
        self,
        number: int,
        mode: FilPiloteMode,
    ) -> None:
        """Set one pilot wire output."""

        _LOGGER.debug(
            "Setting FP%d to %s",
            number,
            mode.name,
        )

        await self._command(
            setfp=f"{number}{mode.value}",
        )

    async def async_set_all_fil_pilote(
        self,
        modes: list[FilPiloteMode],
    ) -> None:
        """Set every pilot wire output."""

        command = "".join(mode.value for mode in modes)

        _LOGGER.debug(
            "Setting all pilot wire outputs: %s",
            command,
        )

        await self._command(
            fp=command,
        )

    #
    # ---------------------------------------------------------
    # Maintenance
    # ---------------------------------------------------------
    #

    async def async_restart(self) -> None:
        """Restart Remora."""

        _LOGGER.info(
            "Restarting Remora",
        )

        with contextlib.suppress(
            TimeoutError,
            aiohttp.ClientError,
            CannotConnect,
        ):
            await self._get_json("reset")
