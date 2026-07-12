"""API client for Remora."""

from __future__ import annotations

import asyncio
import contextlib
from enum import Enum, StrEnum
from typing import Any

import aiohttp


class CannotConnect(Exception):
    """Unable to communicate with Remora."""


class FilPiloteMode(StrEnum):
    """_summary_.

    Args:
        str (_type_): _description_
        Enum (_type_): _description_
    """

    COMFORT = "C"
    ARRET = "A"
    ECO = "E"
    HORS_GEL = "H"
    DELESTAGE = "D"
    ECO1 = "1"
    ECO2 = "2"


class RelaisMode(Enum):
    """_summary_.

    Args:
        Enum (_type_): _description_
    """

    ARRET = 0
    MARCHE_FORCEE = 1
    AUTOMATIQUE = 2


class RelaisEtat(Enum):
    """_summary_.

    Args:
        Enum (_type_): _description_
    """

    OUVERT = 0
    FERME = 1


class RemoraApi:
    """Remora HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
    ) -> None:
        """_summary_.

        Args:
            session (aiohttp.ClientSession): _description_
            host (str): _description_
        """

        self._session = session
        self._base_url = f"http://{host}"

    #
    # ------------------------------------------------------------------
    # Low level HTTP
    # ------------------------------------------------------------------
    #

    async def _get_json(self, endpoint: str) -> Any:
        """GET endpoint and return JSON."""

        async with self._session.get(
            f"{self._base_url}/{endpoint}",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as response:
            response.raise_for_status()

            # Remora retourne parfois text/json...
            return await response.json(content_type=None)

    async def _command(self, **params) -> bool:
        """Send a command to Remora."""

        result = await self._get_json("?" + "&".join(f"{k}={v}" for k, v in params.items()))

        return result["response"] == 0

    #
    # ------------------------------------------------------------------
    # Device information
    # ------------------------------------------------------------------
    #

    async def async_get_system_info(self) -> dict[str, str]:
        """Return system information."""

        data = await self._get_json("system.json")

        return {item["na"]: item["va"] for item in data}

    async def async_get_device_info(self) -> dict[str, str]:
        """Return information used by Home Assistant."""

        system = await self.async_get_system_info()

        return {
            "unique_id": system["Chip ID"],
            "manufacturer": "Remora",
            "model": system["Version Matériel"],
            "sw_version": system["Version Logiciel"],
            "hw_version": system["Version Matériel"],
            "name": "Remora",
        }

    #
    # ------------------------------------------------------------------
    # Sensors
    # ------------------------------------------------------------------
    #

    async def async_get_uptime(self) -> str:
        """_summary_.

        Returns:
            str: _description_
        """
        return (await self._get_json("uptime"))["uptime"]

    async def async_get_relais(self) -> dict:
        """_summary_.

        Returns:
            dict: _description_
        """

        data = await self._get_json("relais")

        return {
            "relais": RelaisEtat(data["relais"]),
            "fnct_relais": RelaisMode(data["fnct_relais"]),
        }

    async def async_get_fil_pilote(self) -> dict[str, FilPiloteMode]:
        """_summary_.

        Returns:
            dict[str, FilPiloteMode]: _description_
        """

        data = await self._get_json("fp")

        return {key: FilPiloteMode(value) for key, value in data.items()}

    async def async_get_teleinfo(self) -> dict | None:
        """_summary_.

        Returns:
            dict | None: _description_
        """

        try:
            return await self._get_json("tinfo")

        except aiohttp.ClientResponseError as err:
            if err.status == 404:
                return None
            raise

    async def async_get_delestage(self):
        """_summary_.

        Returns:
            _type_: _description_
        """

        return await self._get_json("delestage")

    #
    # ------------------------------------------------------------------
    # Complete refresh
    # ------------------------------------------------------------------
    #

    async def async_get_all_data(self):
        """_summary_.

        Returns:
            _type_: _description_
        """

        system, relais, fp, teleinfo = await asyncio.gather(
            self.async_get_system_info(),
            self.async_get_relais(),
            self.async_get_fil_pilote(),
            self.async_get_teleinfo(),
        )

        return {
            "system": system,
            "relais": relais,
            "fp": fp,
            "teleinfo": teleinfo,
        }

    #
    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    #

    async def async_set_relais(
        self,
        state: RelaisEtat,
    ) -> bool:
        """_summary_.

        Args:
            state (RelaisEtat): _description_

        Returns:
            bool: _description_
        """

        return await self._command(
            relais=state.value,
        )

    async def async_set_relais_mode(
        self,
        mode: RelaisMode,
    ) -> bool:
        """_summary_.

        Args:
            mode (RelaisMode): _description_

        Returns:
            bool: _description_
        """

        return await self._command(
            frelais=mode.value,
        )

    async def async_set_fil_pilote(
        self,
        number: int,
        mode: FilPiloteMode,
    ) -> bool:
        """_summary_.

        Args:
            number (int): _description_
            mode (FilPiloteMode): _description_

        Returns:
            bool: _description_
        """

        return await self._command(
            setfp=f"{number}{mode.value}",
        )

    async def async_set_all_fil_pilote(
        self,
        modes: list[FilPiloteMode | None],
    ) -> bool:
        """_summary_.

        Args:
            modes (list[FilPiloteMode  |  None]): _description_

        Returns:
            bool: _description_
        """

        command = "".join(mode.value if mode else "-" for mode in modes)

        return await self._command(
            fp=command,
        )

    #
    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    #

    async def async_restart(self) -> bool:
        """Redémarre le boîtier Remora.

        Returns:
            bool: True si la commande a été envoyée.
        """
        with contextlib.suppress(TimeoutError, aiohttp.ClientError):
            await self._get_json("reset")

        return True
