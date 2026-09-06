"""Sensor platform for TimNet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    COLOUR_MAP,
    DAMPER_INIT,
    DOMAIN,
    DOOR_OPEN,
    FUEL_MAP,
    MODE_MAP,
    RELOAD_MAP,
    SDS_SENSITIVITY_MAP,
    STATUS_MAP,
    TEMP_SPECIAL_LABELS,
    TEMP_SPECIALS,
)
from .coordinator import TimNetCoordinator


@dataclass(frozen=True, kw_only=True)
class TimNetSensorDescription(SensorEntityDescription):
    """TimNet sensor description."""

    value_fn: Callable[[dict[str, Any]], Any]
    enum_map: dict[int, str] | None = None


def _door_value(data: dict[str, Any]) -> str:
    return "open" if data.get("door") == DOOR_OPEN else "closed"


def _damper_value(data: dict[str, Any]) -> int | str:
    val = data.get("damper")
    if val == DAMPER_INIT:
        return "initializing"
    return val


def _sds_value(data: dict[str, Any]) -> str:
    code = data.get("sds", -1)
    if code == 255:
        return "off"
    sens = code // 10
    active = code % 10
    base = SDS_SENSITIVITY_MAP.get(sens, "unknown")
    suffix = "active" if active == 1 else "inactive"
    return f"{base}_{suffix}"


def _fault_value(data: dict[str, Any]) -> str:
    code = int(data.get("fault") or 0)
    if code == 0:
        return "none"
    parts: list[str] = []
    if code & 1:
        parts.append("t1")
    if code & 2:
        parts.append("t2")
    if code & 8:
        parts.append("door")
    return "_".join(parts) if parts else f"code_{code}"


def _temp_value(data: dict[str, Any]) -> float | str | None:
    raw = data.get("t1_raw")
    if raw is None:
        return None
    if raw in TEMP_SPECIALS:
        return TEMP_SPECIAL_LABELS[raw]
    return round(raw * 0.1, 1)


SENSORS: tuple[TimNetSensorDescription, ...] = (
    TimNetSensorDescription(
        key="temperature_t1",
        translation_key="temperature_t1",
        value_fn=_temp_value,
        icon="mdi:thermometer",
    ),
    TimNetSensorDescription(
        key="burn_duration",
        translation_key="burn_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("burn_seconds"),
        icon="mdi:timer-sand",
    ),
    TimNetSensorDescription(
        key="damper_position",
        translation_key="damper_position",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_damper_value,
        icon="mdi:valve",
    ),
    TimNetSensorDescription(
        key="door",
        translation_key="door",
        device_class=SensorDeviceClass.ENUM,
        options=["open", "closed"],
        value_fn=_door_value,
        icon="mdi:door",
    ),
    TimNetSensorDescription(
        key="mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(MODE_MAP.values()),
        value_fn=lambda d: MODE_MAP.get(d.get("mode"), "unknown"),
        icon="mdi:fire",
    ),
    TimNetSensorDescription(
        key="fuel",
        translation_key="fuel",
        device_class=SensorDeviceClass.ENUM,
        options=list(FUEL_MAP.values()),
        value_fn=lambda d: FUEL_MAP.get(d.get("fuel"), "unknown"),
        icon="mdi:pine-tree",
    ),
    TimNetSensorDescription(
        key="reload_offset",
        translation_key="reload_offset",
        device_class=SensorDeviceClass.ENUM,
        options=list(RELOAD_MAP.values()),
        value_fn=lambda d: RELOAD_MAP.get(d.get("reload"), "unknown"),
        icon="mdi:plus-minus-variant",
    ),
    TimNetSensorDescription(
        key="sds",
        translation_key="sds",
        value_fn=_sds_value,
        icon="mdi:tune-vertical",
    ),
    TimNetSensorDescription(
        key="temperature_colour",
        translation_key="temperature_colour",
        device_class=SensorDeviceClass.ENUM,
        options=list(COLOUR_MAP.values()),
        value_fn=lambda d: COLOUR_MAP.get(d.get("colour"), "unknown"),
        icon="mdi:palette",
    ),
    TimNetSensorDescription(
        key="fault",
        translation_key="fault",
        value_fn=_fault_value,
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    TimNetSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=list(STATUS_MAP.values()),
        value_fn=lambda d: STATUS_MAP.get(d.get("status"), "unknown"),
        icon="mdi:information-outline",
    ),
    TimNetSensorDescription(
        key="reload_count",
        translation_key="reload_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("reload_count"),
        icon="mdi:counter",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TimNet sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TimNetCoordinator = data["coordinator"]
    device_info = data["device_info"]
    device_unique_id = data["device_unique_id"]

    async_add_entities(
        TimNetSensor(coordinator, device_info, device_unique_id, desc)
        for desc in SENSORS
    )


class TimNetSensor(CoordinatorEntity[TimNetCoordinator], SensorEntity):
    """TimNet sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TimNetCoordinator,
        device_info: dict,
        device_unique_id: str,
        description: TimNetSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{device_unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(**device_info)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Unit only when temperature is numeric."""
        if self.entity_description.key == "temperature_t1":
            raw = (self.coordinator.data or {}).get("t1_raw")
            if raw in TEMP_SPECIALS or raw is None:
                return None
            return UnitOfTemperature.CELSIUS
        if self.entity_description.key == "damper_position":
            val = (self.coordinator.data or {}).get("damper")
            if val == DAMPER_INIT:
                return None
            return PERCENTAGE
        return self.entity_description.native_unit_of_measurement

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Device class only for numeric temperature."""
        if self.entity_description.key == "temperature_t1":
            raw = (self.coordinator.data or {}).get("t1_raw")
            if raw in TEMP_SPECIALS or raw is None:
                return None
            return SensorDeviceClass.TEMPERATURE
        return self.entity_description.device_class

    @property
    def state_class(self) -> SensorStateClass | None:
        if self.entity_description.key == "temperature_t1":
            raw = (self.coordinator.data or {}).get("t1_raw")
            if raw in TEMP_SPECIALS or raw is None:
                return None
            return SensorStateClass.MEASUREMENT
        return self.entity_description.state_class

    @property
    def options(self) -> list[str] | None:
        """ENUM options; extend with unknown when needed."""
        opts = self.entity_description.options
        if not opts:
            return None
        value = self.native_value
        if isinstance(value, str) and value not in opts:
            return [*opts, value]
        return list(opts)
