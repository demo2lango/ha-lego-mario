from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from . import LegoMarioCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: LegoMarioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LegoMarioBarcodeSensor(coordinator, entry),
        LegoMarioPantsSensor(coordinator, entry)
    ])

class LegoMarioBaseSensor(SensorEntity):
    def __init__(self, coordinator: LegoMarioCoordinator, entry: ConfigEntry):
        self.coordinator = coordinator
        self.entry = entry

    async def async_added_to_hass(self):
        self.coordinator.register_callback(self.async_write_ha_state)

    @property
    def should_poll(self) -> bool:
        return False

class LegoMarioBarcodeSensor(LegoMarioBaseSensor):
    @property
    def name(self):
        return f"{self.entry.title} Scanned Item"

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_barcode"

    @property
    def icon(self):
        return "mdi:barcode-scan"

    @property
    def native_value(self):
        return self.coordinator.barcode

class LegoMarioPantsSensor(LegoMarioBaseSensor):
    @property
    def name(self):
        return f"{self.entry.title} Pants"

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_pants"

    @property
    def icon(self):
        return "mdi:format-vertical-align-bottom"

    @property
    def native_value(self):
        return self.coordinator.pants
