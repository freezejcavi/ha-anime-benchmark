from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .anilist import AniListClient
from .const import DOMAIN, PLATFORMS, STATIC_URL
from .model import ModelBundle
from .runtime import BenchmarkRuntime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    component_dir = Path(__file__).parent
    bundle = await hass.async_add_executor_job(ModelBundle.load, component_dir / "model_bundle.json")
    runtime = BenchmarkRuntime(AniListClient(async_get_clientsession(hass)), bundle)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(component_dir / "static"), False)]
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
