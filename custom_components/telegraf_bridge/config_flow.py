"""Config flow for Telegraf Bridge.

Setup step just needs HA's core `mqtt` integration to already be configured
(we depend on it for the broker connection, no separate credentials - see
Phase 0 decisions). Options flow lets the user override manufacturer/model/
display name for hosts the coordinator has already discovered.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_MANUFACTURER = "manufacturer"
CONF_MODEL = "model"
CONF_NAME = "name"
CONF_HOST = "host"
CONF_HOST_OVERRIDES = "host_overrides"


class TelegrafBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Telegraf Bridge."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        if not self.hass.config_entries.async_entries("mqtt"):
            return self.async_abort(reason="mqtt_not_configured")

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Telegraf Bridge", data=user_input)

        schema = vol.Schema({vol.Optional(CONF_TOPIC, default=DEFAULT_TOPIC): str})
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return TelegrafBridgeOptionsFlow(config_entry)


class TelegrafBridgeOptionsFlow(config_entries.OptionsFlow):
    """Per-host manufacturer/model/display name overrides."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._selected_host: str | None = None

    def _discovered_host_ids(self) -> list[str]:
        """Host ids the coordinator has seen so far, for this entry."""
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if coordinator is None:
            return []
        return sorted({host_id for host_id, _metric in coordinator.known_pairs})

    async def async_step_init(self, user_input: dict | None = None):
        """Choose which discovered host to edit."""
        host_ids = self._discovered_host_ids()
        if not host_ids:
            return self.async_abort(reason="no_hosts_discovered")

        if user_input is not None:
            self._selected_host = user_input[CONF_HOST]
            return await self.async_step_host()

        schema = vol.Schema({vol.Required(CONF_HOST): vol.In(host_ids)})
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_host(self, user_input: dict | None = None):
        """Edit the selected host's manufacturer/model/name override."""
        host_id = self._selected_host
        overrides = dict(self.config_entry.options.get(CONF_HOST_OVERRIDES, {}))
        current = overrides.get(host_id, {})

        if user_input is not None:
            overrides[host_id] = {key: value for key, value in user_input.items() if value}
            new_options = {**self.config_entry.options, CONF_HOST_OVERRIDES: overrides}
            return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Optional(CONF_MANUFACTURER, default=current.get(CONF_MANUFACTURER, "")): str,
                vol.Optional(CONF_MODEL, default=current.get(CONF_MODEL, "")): str,
                vol.Optional(CONF_NAME, default=current.get(CONF_NAME, "")): str,
            }
        )
        return self.async_show_form(step_id="host", data_schema=schema)
