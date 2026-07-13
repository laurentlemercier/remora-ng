"""Config flow for Remora integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .remora import CannotConnect, RemoraApi

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)

STEP_OPTIONS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


async def async_get_device_info(hass: HomeAssistant, host: str) -> dict[str, str]:
    """Valid la connection à Remora et retourne les infos de l'appareil.

    Lève CannotConnect si le boîtier est injoignable.
    """

    session = async_get_clientsession(hass)
    api = RemoraApi(session, host)

    try:
        return await api.async_get_device_info()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise CannotConnect(f"Impossible de contacter Remora sur {host}") from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le config flow pour Remora."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Étape initiale : saisie du host."""

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            try:
                device_info = await async_get_device_info(self.hass, host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Erreur inattendue lors de la validation")
                errors["base"] = "unknown"
            else:
                # Unicité basée sur l'identifiant matériel réel (Chip ID),
                # pas sur l'IP qui peut changer (DHCP).
                await self.async_set_unique_id(device_info["unique_id"])
                self._abort_if_unique_id_configured(updates=user_input)

                return self.async_create_entry(
                    title=host,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Permet de modifier l'intervalle de rafraîchissement après coup."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Gère les options de l'intégration Remora."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise l'options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Gère les options (intervalle de rafraîchissement)."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): int,
                }
            ),
        )
