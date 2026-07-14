"""Config flow for Remora integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from custom_components.remora.api import CannotConnect, RemoraApi
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.models import RemoraDevice
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


async def async_validate_connection(hass: HomeAssistant, host: str) -> RemoraDevice:
    """Validates the connection to Remora and returns the device information.

    Raise CannotConnect if the box is unreachable (already managed by
    RemoraApi. _get_json, which converts network errors/timeout).
    """

    session = async_get_clientsession(hass)
    api = RemoraApi(session, host)

    return await api.async_validate_connection()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le config flow pour Remora."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Étape initiale : saisie du host."""

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            try:
                device = await async_validate_connection(self.hass, host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Erreur inattendue lors de la validation")
                errors["base"] = "unknown"
            else:
                # Unicité basée sur l'identifiant matériel réel (Chip ID),
                # pas sur l'IP qui peut changer (DHCP).
                await self.async_set_unique_id(device.unique_id)
                self._abort_if_unique_id_configured(updates=user_input)

                return self.async_create_entry(
                    title=f"Remora ({device.unique_id})",
                    data=user_input,
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
        """Permet de modifier l'intervalle de rafraîchissement après coup."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Gère les options de l'intégration Remora."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
