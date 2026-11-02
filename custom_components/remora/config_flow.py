"""Config flow for Remora integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from custom_components.remora.api import CannotConnect, RemoraApi
from custom_components.remora.api.models import RemoraDevice
from custom_components.remora.const import (
    CONF_DEBUG,
    CONF_ENABLE_CLIMATE,
    CONF_ENABLE_SELECT,
    DEFAULT_DEBUG,
    DEFAULT_ENABLE_CLIMATE,
    DEFAULT_ENABLE_SELECT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_ENABLE_CLIMATE, default=DEFAULT_ENABLE_CLIMATE): bool,
        vol.Optional(CONF_ENABLE_SELECT, default=DEFAULT_ENABLE_SELECT): bool,
    }
)


async def async_validate_connection(hass: HomeAssistant, host: str) -> RemoraDevice:
    """Validate the connection to Remora and return device information.

    Raises CannotConnect if the unit is unreachable (handled by
    RemoraApi._get_json, which converts network errors/timeouts).
    """

    session = async_get_clientsession(hass)
    api = RemoraApi(session, host)

    return await api.async_validate_connection()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow handler for Remora."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Initial step: host entry."""

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            try:
                device = await async_validate_connection(self.hass, host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during validation")
                errors["base"] = "unknown"
            else:
                # Use the real hardware identifier (Chip ID) for uniqueness,
                # not the IP which can change via DHCP.
                await self.async_set_unique_id(device.unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title=f"Remora ({device.unique_id})",
                    data={CONF_HOST: host},
                    options={
                        CONF_ENABLE_CLIMATE: user_input.get(CONF_ENABLE_CLIMATE, DEFAULT_ENABLE_CLIMATE),
                        CONF_ENABLE_SELECT: user_input.get(CONF_ENABLE_SELECT, DEFAULT_ENABLE_SELECT),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow handler."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Options flow for Remora.

    Do not define `__init__` to store `config_entry`: since HA 2025.12,
    `self.config_entry` is a read-only property injected automatically by
    the flow manager.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options (refresh interval, debug mode)."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
        current_debug = self.config_entry.options.get(
            CONF_DEBUG,
            DEFAULT_DEBUG,
        )
        current_enable_climate = self.config_entry.options.get(
            CONF_ENABLE_CLIMATE,
            DEFAULT_ENABLE_CLIMATE,
        )
        current_enable_select = self.config_entry.options.get(
            CONF_ENABLE_SELECT,
            DEFAULT_ENABLE_SELECT,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_DEBUG,
                        default=current_debug,
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_CLIMATE,
                        default=current_enable_climate,
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_SELECT,
                        default=current_enable_select,
                    ): bool,
                }
            ),
        )
