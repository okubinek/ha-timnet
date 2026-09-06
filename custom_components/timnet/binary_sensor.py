"""Binary sensor platform for TimNet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MODEL,
    CONF_RELAY1_NAME,
    CONF_RELAY2_NAME,
    DOOR_OPEN,
    DOMAIN,
    MODEL_100,
    RELAY_ON,
    model_supports_t2,
)
from .coordinator import TimNetCoordinator


@dataclass(frozen=True, kw_only=True)
class TimNetBinarySensorDescription(BinarySensorEntityDescription):
    """TimNet binary sensor description."""

    is_on_fn: Callable[[dict], bool | None]
    icon_on: str | None = None
    icon_off: str | None = None
    requires_t2: bool = False
    name_option_key: str | None = None


BINARY_SENSORS: tuple[TimNetBinarySensorDescription, ...] = (
    TimNetBinarySensorDescription(
        key="door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        is_on_fn=lambda d: d.get("door") == DOOR_OPEN,
        icon_on="mdi:door-open",
        icon_off="mdi:door-closed",
    ),
    TimNetBinarySensorDescription(
        key="sds_active",
        translation_key="sds_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda d: (
            None
            if d.get("sds") is None or d.get("sds") == 255
            else (d.get("sds", 0) % 10) == 1
        ),
        icon_on="mdi:motion-sensor",
        icon_off="mdi:motion-sensor-off",
    ),
    TimNetBinarySensorDescription(
        key="relay_1",
        translation_key="relay_1",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda d: d.get("rele1") == RELAY_ON,
        icon_on="mdi:electric-switch-closed",
        icon_off="mdi:electric-switch",
        requires_t2=True,
        name_option_key=CONF_RELAY1_NAME,
    ),
    TimNetBinarySensorDescription(
        key="relay_2",
        translation_key="relay_2",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda d: d.get("rele2") == RELAY_ON,
        icon_on="mdi:electric-switch-closed",
        icon_off="mdi:electric-switch",
        requires_t2=True,
        name_option_key=CONF_RELAY2_NAME,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TimNet binary sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    model = entry.data.get(CONF_MODEL, MODEL_100)

    entities: list[TimNetBinarySensor] = []
    for desc in BINARY_SENSORS:
        if desc.requires_t2 and not model_supports_t2(model):
            continue
        name_override = None
        if desc.name_option_key:
            name_override = (entry.options.get(desc.name_option_key) or "").strip() or None
        entities.append(
            TimNetBinarySensor(
                data["coordinator"],
                data["device_info"],
                data["device_unique_id"],
                desc,
                name_override=name_override,
            )
        )
    async_add_entities(entities)


class TimNetBinarySensor(CoordinatorEntity[TimNetCoordinator], BinarySensorEntity):
    """TimNet binary sensor."""

    _attr_has_entity_name = True
    entity_description: TimNetBinarySensorDescription

    def __init__(
        self,
        coordinator: TimNetCoordinator,
        device_info: dict,
        device_unique_id: str,
        description: TimNetBinarySensorDescription,
        name_override: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{device_unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(**device_info)
        if name_override:
            self._attr_name = name_override
            self._attr_translation_key = None

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)

    @property
    def icon(self) -> str | None:
        desc = self.entity_description
        if self.is_on and desc.icon_on:
            return desc.icon_on
        if self.is_on is False and desc.icon_off:
            return desc.icon_off
        return desc.icon
