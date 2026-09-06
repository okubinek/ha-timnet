"""Button platform for TimNet."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REG_START_W, WRITE_START
from .coordinator import TimNetCoordinator
from .modbus_client import TimNetModbusClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TimNet buttons."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TimNetStartButton(
                data["coordinator"],
                data["client"],
                data["device_info"],
                data["device_unique_id"],
            )
        ]
    )


class TimNetStartButton(CoordinatorEntity[TimNetCoordinator], ButtonEntity):
    """Start regulation / burning (write register 0 = 1)."""

    _attr_has_entity_name = True
    _attr_translation_key = "start_regulation"
    _attr_icon = "mdi:fire"

    def __init__(
        self,
        coordinator: TimNetCoordinator,
        client: TimNetModbusClient,
        device_info: dict,
        device_unique_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._attr_unique_id = f"{device_unique_id}_start_regulation"
        self._attr_device_info = DeviceInfo(**device_info)

    async def async_press(self) -> None:
        """Start the regulation process."""
        if not await self._client.write_register(REG_START_W, WRITE_START):
            raise HomeAssistantError("Failed to start TimNet regulation")
        await self.coordinator.async_request_refresh()
