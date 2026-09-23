from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import AnimeBenchmarkEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([AnimeBenchmarkRating(hass.data[DOMAIN][entry.entry_id], entry.entry_id)])


class AnimeBenchmarkRating(AnimeBenchmarkEntity, SensorEntity):
    _attr_translation_key = "rating"
    _attr_unique_id = "anime_benchmark_rating"
    _attr_icon = "mdi:star-circle-outline"

    @property
    def native_value(self):
        return None if not self.runtime.result else self.runtime.result["rating"]

    @property
    def extra_state_attributes(self):
        result = dict(self.runtime.result or {})
        result["busy"] = self.runtime.busy
        result["error"] = self.runtime.error
        return result
