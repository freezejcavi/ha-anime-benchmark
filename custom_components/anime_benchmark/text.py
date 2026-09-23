from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import AnimeBenchmarkEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([AnimeBenchmarkTitle(hass.data[DOMAIN][entry.entry_id], entry.entry_id)])


class AnimeBenchmarkTitle(AnimeBenchmarkEntity, TextEntity):
    _attr_translation_key = "title"
    _attr_unique_id = "anime_benchmark_title"
    _attr_native_max = 255

    @property
    def native_value(self) -> str:
        return self.runtime.query

    async def async_set_value(self, value: str) -> None:
        self.runtime.set_query(value)
