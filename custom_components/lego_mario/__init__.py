import asyncio
import logging

from bleak import BleakClient
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import COLOR_MAP, DOMAIN, LEGO_CHARACTERISTIC_UUID, PANTS_MAP

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LEGO Mario from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # 统一转换小写地址
    address = entry.data["address"].lower()
    coordinator = LegoMarioCoordinator(hass, entry, address)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_create_background_task(
        hass, coordinator.async_start(), "lego_mario_ble_loop"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: LegoMarioCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class LegoMarioCoordinator:
    """Manage the BLE connection and sensor updates for LEGO Mario."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, address: str) -> None:
        """Initialize coordinator."""
        self.hass = hass
        self.entry = entry
        self.address = address.lower()
        self.connected = False

        self.barcode = "None"
        self.pants = "Unknown"
        self.client: BleakClient | None = None

        self._running = True
        self._callbacks = []
        self._connect_event = asyncio.Event()
        self._unsubscribe_ble = None

    def register_callback(self, cb):
        """Register entity update callback."""
        self._callbacks.append(cb)

    def _notify_update(self):
        """Notify all entities to update HA state."""
        for cb in self._callbacks:
            cb()

    @callback
    def _async_ble_device_discovered(
        self, service_info: bluetooth.BluetoothServiceInfoBleak, change: bluetooth.BluetoothChange
    ) -> None:
        """当 HA 捕获到玛丽欧开机广播时，立即触发唤醒并连接"""
        if not self.connected:
            _LOGGER.debug("捕获到 LEGO Mario (%s) 广播包，触发自动重连", self.address)
            self._connect_event.set()

    async def async_start(self):
        """Main BLE loop with active reconnect."""
        # 监听蓝牙广播，开机即连
        self._unsubscribe_ble = bluetooth.async_register_callback(
            self.hass,
            self._async_ble_device_discovered,
            {"address": self.address},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )

        while self._running:
            try:
                ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )

                if not ble_device:
                    self._connect_event.clear()
                    try:
                        # 轮询兼顾广播触发
                        await asyncio.wait_for(self._connect_event.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        pass
                    continue

                _LOGGER.info("尝试连接 LEGO Mario (%s)...", self.address)
                self.client = await establish_connection(
                    BleakClient, ble_device, self.address
                )

                self.connected = True
                self._notify_update()
                _LOGGER.info("LEGO Mario 连接成功！")

                # 1. 订阅消息接收
                await self.client.start_notify(
                    LEGO_CHARACTERISTIC_UUID, self._parse_lego_message
                )

                # 2. 切换 Port 0x01 到颜色/Tag 模式 (Input Format Setup)
                await self.client.write_gatt_char(
                    LEGO_CHARACTERISTIC_UUID,
                    bytearray([0x0A, 0x00, 0x41, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01]),
                    response=False,
                )
                await asyncio.sleep(0.2)

                # 3. 切换 Port 0x02 到裤子/模式
                await self.client.write_gatt_char(
                    LEGO_CHARACTERISTIC_UUID,
                    bytearray([0x0A, 0x00, 0x41, 0x02, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01]),
                    response=False,
                )

                # 维持连接状态
                while self.client.is_connected and self._running:
                    await asyncio.sleep(1)

            except Exception as err:
                _LOGGER.warning("LEGO Mario 蓝牙连接异常或已断开: %s", err)
            finally:
                self.connected = False
                self._notify_update()
                await asyncio.sleep(2)

    async def async_stop(self):
        """Stop connection and cleanup."""
        self._running = False
        if self._unsubscribe_ble:
            self._unsubscribe_ble()
            self._unsubscribe_ble = None
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    @callback
    def _parse_lego_message(self, sender: int, data: bytearray):
        """Parse incoming BLE messages from LEGO Mario."""
        if len(data) < 5:
            return

        msg_type = data[2]

        # 0x45 代表 Port Value Notification
        if msg_type == 0x45:
            port_id = data[3]
            val = data[4] | (data[5] << 8) if len(data) >= 6 else data[4]

            # 核心修正 1：过滤 65535 (0xFFFF 悬空无效值)
            if val == 65535 or val == 0xFFFF:
                return

            _LOGGER.debug("LEGO Mario 传感器数据更新: Port=%s, Value=%s", port_id, val)

            # 核心修正 2：裤子与条形码数据分类映射
            if val in PANTS_MAP:
                self.pants = PANTS_MAP[val]
            elif data[4] in COLOR_MAP:
                self.barcode = COLOR_MAP[data[4]]
            else:
                self.barcode = f"Tag_{val}"

            # 触发 Home Assistant 事件（便于在自动化逻辑中使用）
            self.hass.bus.async_fire(
                "lego_mario_scanned",
                {
                    "address": self.address,
                    "port": port_id,
                    "raw_code": val,
                    "pants": self.pants,
                    "barcode": self.barcode,
                },
            )

            self._notify_update()
