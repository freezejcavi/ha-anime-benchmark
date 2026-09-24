from __future__ import annotations

from pathlib import Path
import json

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .anilist import AniListClient
from .catalog import CatalogIndex
from .const import (
    CONF_GITHUB_TOKEN,
    CONF_PROFILE_ID,
    CONF_TRACKER_BRANCH,
    CONF_TRACKER_REPOSITORY,
    DEFAULT_PROFILE_ID,
    DEFAULT_TRACKER_BRANCH,
    DEFAULT_TRACKER_REPOSITORY,
    DOMAIN,
    PLATFORMS,
    STATIC_URL,
)
from .frontend import async_ensure_lovelace_resource
from .github_writer import GitHubTransactionWriter
from .model import ModelBundle
from .runtime import BenchmarkRuntime

SERVICE_SEARCH = "search"
SERVICE_ADD_LATER = "add_later"


def _read_manifest_version(component_dir: Path) -> str:
    manifest = json.loads((component_dir / "manifest.json").read_text(encoding="utf-8"))
    return str(manifest["version"])

SERVICE_SEARCH_SCHEMA = vol.Schema(
    {
        vol.Required("query"): cv.string,
        vol.Optional("anilist_id"): vol.Coerce(int),
    }
)
SERVICE_ADD_LATER_SCHEMA = vol.Schema(
    {
        vol.Required("anilist_id"): vol.Coerce(int),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def async_handle_search(call: ServiceCall) -> None:
        runtimes = hass.data.get(DOMAIN, {})
        if not runtimes:
            raise ServiceValidationError("Anime Benchmark config entry is not loaded")
        runtime = next(iter(runtimes.values()))
        await runtime.search(call.data["query"], call.data.get("anilist_id"))

    async def async_handle_add_later(call: ServiceCall) -> None:
        runtimes = hass.data.get(DOMAIN, {})
        if not runtimes:
            raise ServiceValidationError("Anime Benchmark config entry is not loaded")
        runtime = next(iter(runtimes.values()))
        await runtime.add_later(call.data["anilist_id"])

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH,
        async_handle_search,
        schema=SERVICE_SEARCH_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_LATER,
        async_handle_add_later,
        schema=SERVICE_ADD_LATER_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    component_dir = Path(__file__).parent
    bundle = await hass.async_add_executor_job(ModelBundle.load, component_dir / "model_bundle.json")
    catalog = await hass.async_add_executor_job(CatalogIndex.load, component_dir / "catalog_index.json")
    session = async_get_clientsession(hass)
    options = entry.options
    writer = GitHubTransactionWriter(
        session,
        options.get(CONF_GITHUB_TOKEN),
        options.get(CONF_TRACKER_REPOSITORY, DEFAULT_TRACKER_REPOSITORY),
        options.get(CONF_TRACKER_BRANCH, DEFAULT_TRACKER_BRANCH),
        options.get(CONF_PROFILE_ID, DEFAULT_PROFILE_ID),
    )
    runtime = BenchmarkRuntime(AniListClient(session), bundle, catalog, writer)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(component_dir / "static"), False)]
    )

    version = await hass.async_add_executor_job(_read_manifest_version, component_dir)
    await async_ensure_lovelace_resource(hass, version)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
