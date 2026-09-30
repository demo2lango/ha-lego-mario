from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from . import LegoMarioCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: LegoMarioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LegoMarioConnectionSensor(coordinator, entry)])

class LegoMarioConnectionSensor(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: LegoMarioCoordinator, entry: ConfigEntry):
        self.coordinator = coordinator
        self.entry = entry

    async def async_added_to_hass(self):
        self.coordinator.register_callback(self.async_write_ha_state)

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def name(self):
        return f"{self.entry.title} Connection"

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_connection"

    @property
    def is_on(self):
        return self.coordinator.connected
