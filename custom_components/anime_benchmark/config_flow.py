from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_GITHUB_TOKEN,
    CONF_PROFILE_ID,
    CONF_TRACKER_BRANCH,
    CONF_TRACKER_REPOSITORY,
    DEFAULT_PROFILE_ID,
    DEFAULT_TRACKER_BRANCH,
    DEFAULT_TRACKER_REPOSITORY,
    DOMAIN,
)


class AnimeBenchmarkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Anime Benchmark", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AnimeBenchmarkOptionsFlow(config_entry)


class AnimeBenchmarkOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        current = dict(self.config_entry.options)

        if user_input is not None:
            token = (user_input.get(CONF_GITHUB_TOKEN) or "").strip()
            if token:
                current[CONF_GITHUB_TOKEN] = token
            current[CONF_TRACKER_REPOSITORY] = (
                user_input.get(CONF_TRACKER_REPOSITORY) or DEFAULT_TRACKER_REPOSITORY
            ).strip()
            current[CONF_TRACKER_BRANCH] = (
                user_input.get(CONF_TRACKER_BRANCH) or DEFAULT_TRACKER_BRANCH
            ).strip()
            current[CONF_PROFILE_ID] = (
                user_input.get(CONF_PROFILE_ID) or DEFAULT_PROFILE_ID
            ).strip()
            return self.async_create_entry(title="", data=current)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_GITHUB_TOKEN,
                    default="",
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                    )
                ),
                vol.Required(
                    CONF_TRACKER_REPOSITORY,
                    default=current.get(
                        CONF_TRACKER_REPOSITORY, DEFAULT_TRACKER_REPOSITORY
                    ),
                ): str,
                vol.Required(
                    CONF_TRACKER_BRANCH,
                    default=current.get(CONF_TRACKER_BRANCH, DEFAULT_TRACKER_BRANCH),
                ): str,
                vol.Required(
                    CONF_PROFILE_ID,
                    default=current.get(CONF_PROFILE_ID, DEFAULT_PROFILE_ID),
                ): str,
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "token_status": (
                    "configured"
                    if current.get(CONF_GITHUB_TOKEN)
                    else "not configured"
                )
            },
        )
