from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import AnimeBenchmarkEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([AnimeBenchmarkCalculate(hass.data[DOMAIN][entry.entry_id], entry.entry_id)])


class AnimeBenchmarkCalculate(AnimeBenchmarkEntity, ButtonEntity):
    _attr_translation_key = "calculate"
    _attr_unique_id = "anime_benchmark_calculate"
    _attr_icon = "mdi:calculator-variant-outline"

    async def async_press(self) -> None:
        await self.runtime.calculate()
