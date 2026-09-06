"""Switch platform for TimNet."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REG_BEEP_W, WRITE_BEEP_OFF, WRITE_BEEP_ON
from .coordinator import TimNetCoordinator
from .modbus_client import TimNetModbusClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TimNet switches."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TimNetBeepSwitch(
                data["coordinator"],
                data["client"],
                data["device_info"],
                data["device_unique_id"],
            )
        ]
    )


class TimNetBeepSwitch(CoordinatorEntity[TimNetCoordinator], SwitchEntity):
    """Acoustic signalling switch (write reg 1, read reg 10)."""

    _attr_has_entity_name = True
    _attr_translation_key = "beep"
    _attr_icon = "mdi:volume-high"

    def __init__(
        self,
        coordinator: TimNetCoordinator,
        client: TimNetModbusClient,
        device_info: dict,
        device_unique_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._attr_unique_id = f"{device_unique_id}_beep"
        self._attr_device_info = DeviceInfo(**device_info)

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("beep") == WRITE_BEEP_ON

    async def async_turn_on(self, **kwargs) -> None:
        if not await self._client.write_register(REG_BEEP_W, WRITE_BEEP_ON):
            raise HomeAssistantError("Failed to enable TimNet beep")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        if not await self._client.write_register(REG_BEEP_W, WRITE_BEEP_OFF):
            raise HomeAssistantError("Failed to disable TimNet beep")
        await self.coordinator.async_request_refresh()
