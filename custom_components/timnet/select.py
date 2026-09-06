"""Select platform for TimNet."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FUEL_MAP,
    FUEL_WRITE,
    MODE_MAP,
    MODE_WRITE,
    REG_PALIVO_W,
    REG_PRILOZ_W,
    REG_REZIM_W,
    REG_SDS_W,
    RELOAD_MAP,
    RELOAD_WRITE,
    SDS_WRITE,
)
from .coordinator import TimNetCoordinator
from .modbus_client import TimNetModbusClient


@dataclass(frozen=True, kw_only=True)
class TimNetSelectDescription(SelectEntityDescription):
    """Select description."""

    data_key: str
    write_address: int
    read_map: dict[int, str]
    write_map: dict[str, int]


SELECTS: tuple[TimNetSelectDescription, ...] = (
    TimNetSelectDescription(
        key="mode",
        translation_key="mode_select",
        icon="mdi:fire",
        options=list(MODE_WRITE.keys()),
        data_key="mode",
        write_address=REG_REZIM_W,
        read_map=MODE_MAP,
        write_map=MODE_WRITE,
    ),
    TimNetSelectDescription(
        key="fuel",
        translation_key="fuel_select",
        icon="mdi:pine-tree",
        options=list(FUEL_WRITE.keys()),
        data_key="fuel",
        write_address=REG_PALIVO_W,
        read_map=FUEL_MAP,
        write_map=FUEL_WRITE,
    ),
    TimNetSelectDescription(
        key="reload_offset",
        translation_key="reload_offset_select",
        icon="mdi:plus-minus-variant",
        options=list(RELOAD_WRITE.keys()),
        data_key="reload",
        write_address=REG_PRILOZ_W,
        read_map=RELOAD_MAP,
        write_map=RELOAD_WRITE,
    ),
    TimNetSelectDescription(
        key="sds",
        translation_key="sds_select",
        icon="mdi:tune-vertical",
        options=list(SDS_WRITE.keys()),
        data_key="sds",
        write_address=REG_SDS_W,
        read_map={},  # special decode
        write_map=SDS_WRITE,
    ),
)


def _current_sds_option(code: int | None) -> str | None:
    if code is None:
        return None
    if code == 255:
        return "off"
    sens = code // 10
    from .const import SDS_SENSITIVITY_MAP

    return SDS_SENSITIVITY_MAP.get(sens)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TimNet selects."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TimNetSelect(
            data["coordinator"],
            data["client"],
            data["device_info"],
            data["device_unique_id"],
            desc,
        )
        for desc in SELECTS
    )


class TimNetSelect(CoordinatorEntity[TimNetCoordinator], SelectEntity):
    """TimNet select entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TimNetCoordinator,
        client: TimNetModbusClient,
        device_info: dict,
        device_unique_id: str,
        description: TimNetSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._client = client
        self._desc = description
        self._attr_unique_id = f"{device_unique_id}_select_{description.key}"
        self._attr_device_info = DeviceInfo(**device_info)
        self._attr_options = list(description.options)

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        if self._desc.key == "sds":
            return _current_sds_option(self.coordinator.data.get("sds"))
        raw = self.coordinator.data.get(self._desc.data_key)
        return self._desc.read_map.get(raw)

    async def async_select_option(self, option: str) -> None:
        value = self._desc.write_map.get(option)
        if value is None:
            raise HomeAssistantError(f"Invalid option: {option}")
        if not await self._client.write_register(self._desc.write_address, value):
            raise HomeAssistantError(f"Failed to write TimNet register {self._desc.write_address}")
        await self.coordinator.async_request_refresh()
