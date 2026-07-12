"""Config flow for remora_ng.

This module provides backwards compatibility for hassfest.
The actual implementation is in the config_flow_handler package.
"""

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .remora import RemoraApi

DOMAIN = "remora_ng"


class RemoraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gère le flux de configuration pour Remora NG."""

    async def async_step_user(self, user_input=None):
        """Étape d'initialisation déclenchée par l'utilisateur."""
        if user_input is not None:
            # 1. On récupère la session HTTP de Home Assistant
            session = async_get_clientsession(self.hass)

            # 2. On extrait le host depuis les données saisies par l'utilisateur
            host = user_input.get("host")

            # 3. On appelle votre logique d'API de manière sécurisée
            api = RemoraApi(session, host)
            info = await api.async_get_device_info()

            # 4. Enregistrement de l'appareil
            await self.async_set_unique_id(info["unique_id"])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=info["name"],
                data=user_input,
            )

        # Si aucun input (premier affichage), Home Assistant doit afficher un formulaire.
        # Note : Pensez à définir un schéma de données (voluptuous) si nécessaire ici.
        return self.async_show_form(step_id="user")
