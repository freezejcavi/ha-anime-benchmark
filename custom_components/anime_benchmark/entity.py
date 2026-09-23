from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .runtime import BenchmarkRuntime


class AnimeBenchmarkEntity(Entity):
    _attr_has_entity_name = True

    def __init__(self, runtime: BenchmarkRuntime, entry_id: str) -> None:
        self.runtime = runtime
        self._entry_id = entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Anime Benchmark",
            manufacturer="freezejcavi",
            model="Local AniList affinity scorer",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.runtime.add_listener(self.async_write_ha_state))
