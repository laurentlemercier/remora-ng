"""coordinator."""

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL


class RemoraCoordinator(DataUpdateCoordinator):
    """_summary_.

    Args:
        DataUpdateCoordinator (_type_): _description_
    """

    def __init__(self, hass, api, logger):
        """_summary_.

        Args:
            hass (bool): _description_
            api (_type_): _description_
            logger (_type_): _description_
        """

        self.api = api

        super().__init__(
            hass,
            logger,
            name="Remora",
            update_method=self._async_update,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update(self):
        """_summary_.

        Raises:
            UpdateFailed: _description_

        Returns:
            _type_: _description_
        """

        try:
            return await self.api.async_get_all_data()

        except Exception as err:
            raise UpdateFailed(err) from err
