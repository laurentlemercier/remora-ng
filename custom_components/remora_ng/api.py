"""API file."""

import asyncio

import aiohttp


class CannotConnect(Exception):
    """Impossible de joindre le Remora."""


class RemoraApi:
    """Client API pour communiquer avec le boîtier Téléinfo Remora."""

    def __init__(self, session, host):
        """_summary_.

        Args:
            session (_type_): _description_
            host (_type_): _description_
        """
        self._session = session
        self._host = host

    async def _get_json(self, endpoint):
        """_summary_.

        Args:
            endpoint (_type_): _description_

        Returns:
            _type_: _description_
        """
        url = f"http://{self._host}/{endpoint}"

        async with self._session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=5),
        ) as response:
            response.raise_for_status()

            return await response.json()

    async def async_test_connection(self):
        """_summary_.

        Raises:
            CannotConnect: _description_
        """
        try:
            await self._get_json("uptime")

        except (TimeoutError, aiohttp.ClientError) as err:
            raise CannotConnect from err

    async def async_get_data(self):
        """_summary_.

        Returns:
            _type_: _description_
        """

        uptime, relais, fp, tinfo = await asyncio.gather(
            self._get_json("uptime"),
            self._get_json("relais"),
            self._get_json("fp"),
            self._get_json("tinfo"),
        )

        return {
            "uptime": uptime,
            "relais": relais,
            "fp": fp,
            "tinfo": tinfo,
        }

    async def async_get_device_info(self):
        """_summary_.

        Raises:
            CannotConnect: _description_

        Returns:
            _type_: _description_
        """

        try:
            data = await self._get_json("uptime")

        except (TimeoutError, aiohttp.ClientError) as err:
            raise CannotConnect from err

        #
        # À adapter selon le JSON réel du Remora.
        #
        return {
            "name": data.get("name", "Remora"),
            "serial": data.get("serial"),
            "version": data.get("version"),
        }
