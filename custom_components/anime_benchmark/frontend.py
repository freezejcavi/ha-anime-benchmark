from __future__ import annotations

import logging

from homeassistant.components.lovelace.const import (
    CONF_RESOURCE_TYPE_WS,
    LOVELACE_DATA,
    MODE_STORAGE,
)
from homeassistant.const import CONF_ID, CONF_URL
from homeassistant.core import HomeAssistant

from .const import STATIC_URL

_LOGGER = logging.getLogger(__name__)

CARD_RESOURCE_PREFIX = f"{STATIC_URL}/anime-benchmark-card"
CARD_RESOURCE_PATH = f"{STATIC_URL}/anime-benchmark-card.impl.js"


async def async_ensure_lovelace_resource(
    hass: HomeAssistant,
    version: str,
) -> None:
    """Create/update our Lovelace resource with a versioned URL.

    A versioned resource URL prevents browsers/service workers from reviving
    an older custom-card module after an integration update.
    """
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        _LOGGER.warning(
            "Lovelace data is unavailable; Anime Benchmark card resource was not auto-managed"
        )
        return

    if lovelace_data.resource_mode != MODE_STORAGE:
        _LOGGER.warning(
            "Lovelace resources are not in storage mode; keep Anime Benchmark resource managed manually"
        )
        return

    resources = lovelace_data.resources

    # Ensures the storage collection is loaded before async_items() is used.
    await resources.async_get_info()

    target_url = f"{CARD_RESOURCE_PATH}?v={version}"
    matches = [
        item
        for item in resources.async_items()
        if str(item.get(CONF_URL, "")).startswith(CARD_RESOURCE_PREFIX)
    ]

    if not matches:
        await resources.async_create_item(
            {
                CONF_RESOURCE_TYPE_WS: "module",
                CONF_URL: target_url,
            }
        )
        _LOGGER.info("Registered Anime Benchmark Lovelace resource %s", target_url)
        return

    primary = matches[0]
    if primary.get(CONF_URL) != target_url or primary.get("type") != "module":
        await resources.async_update_item(
            primary[CONF_ID],
            {
                CONF_RESOURCE_TYPE_WS: "module",
                CONF_URL: target_url,
            },
        )
        _LOGGER.info("Updated Anime Benchmark Lovelace resource to %s", target_url)

    # Remove stale duplicates from earlier manual/loader-based registrations.
    for duplicate in matches[1:]:
        await resources.async_delete_item(duplicate[CONF_ID])
        _LOGGER.info(
            "Removed stale Anime Benchmark Lovelace resource %s",
            duplicate.get(CONF_URL),
        )
