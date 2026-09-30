import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    async_discovered_service_info,
    BluetoothServiceInfoBleak,
)
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LEGO_SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class LegoMarioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LEGO Mario."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._discovered_device: tuple[str, str] | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        # 强制转换为小写，保证 unique_id 绝对一致
        address = discovery_info.address.lower()
        await self.async_set_unique_id(address)

        # 如果这个 MAC 地址已经配置过了，中止并忽略自动发现，不再弹提醒
        self._abort_if_unique_id_configured()

        name = discovery_info.name or "LEGO Mario"
        self._discovered_device = (address, name)
        self.context["title_placeholders"] = {"name": name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None and self._discovered_device:
            address, name = self._discovered_device
            return self.async_create_entry(
                title=name,
                data={"address": address},
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovered_device[1] if self._discovered_device else "LEGO Mario"
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user initiated flow."""
        if user_input is not None:
            address = user_input["address"].lower()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="LEGO Mario", data={"address": address})

        current_ids = self._async_current_ids()
        discovered = {}

        for info in async_discovered_service_info(self.hass):
            addr = info.address.lower()
            if addr not in current_ids and (
                LEGO_SERVICE_UUID in info.service_uuids or "Mario" in (info.name or "")
            ):
                discovered[addr] = f"{info.name or 'LEGO Device'} ({info.address})"

        if not discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("address"): vol.In(discovered)}),
        )
