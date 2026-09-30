import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import bluetooth
from bleak import BleakClient
from bleak_retry_connector import establish_connection

from .const import DOMAIN, LEGO_CHARACTERISTIC_UUID, PANTS_MAP, COLOR_MAP

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    address = entry.data["address"]
    coordinator = LegoMarioCoordinator(hass, entry, address)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_create_background_task(
        hass, coordinator.async_start(), "lego_mario_ble_loop"
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: LegoMarioCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class LegoMarioCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, address: str):
        self.hass = hass
        self.entry = entry
        self.address = address
        self.connected = False
        
        self.barcode = "None"
        self.pants = "Unknown"
        self.client: BleakClient | None = None
        self._running = True
        self._callbacks = []

    def register_callback(self, cb):
        self._callbacks.append(cb)

    def _notify_update(self):
        for cb in self._callbacks:
            cb()

    async def async_start(self):
        while self._running:
            try:
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if not ble_device:
                    await asyncio.sleep(5)
                    continue

                _LOGGER.info("Connecting to LEGO Mario (%s)...", self.address)
                self.client = await establish_connection(
                    BleakClient, ble_device, self.address
                )
                
                self.connected = True
                self._notify_update()

                await self.client.start_notify(
                    LEGO_CHARACTERISTIC_UUID, self._parse_lego_message
                )

                # 订阅传感器端口 notification
                await self.client.write_gatt_char(
                    LEGO_CHARACTERISTIC_UUID,
                    bytearray([0x0A, 0x00, 0x41, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01]),
                    response=False
                )
                
                while self.client.is_connected and self._running:
                    await asyncio.sleep(1)

            except Exception as err:
                _LOGGER.warning("LEGO Mario BLE Disconnected: %s", err)
            finally:
                self.connected = False
                self._notify_update()
                await asyncio.sleep(5)

    async def async_stop(self):
        self._running = False
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    @callback
    def _parse_lego_message(self, sender: int, data: bytearray):
        if len(data) < 3:
            return

        if data[2] == 0x45 and data[3] == 0x01 and len(data) >= 6:
            scanned_id = data[4] | (data[5] << 8)
            
            if scanned_id in PANTS_MAP:
                self.pants = PANTS_MAP[scanned_id]
            elif data[4] in COLOR_MAP:
                self.barcode = COLOR_MAP[data[4]]
            else:
                self.barcode = f"Tag_{scanned_id}"

            self.hass.bus.async_fire("lego_mario_scanned", {
                "address": self.address,
                "code": scanned_id,
                "pants": self.pants,
                "barcode": self.barcode
            })

            self._notify_update()
