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
    CONF_MODEL,
    CONF_T2_NAME,
    DAMPER_INIT,
    DOMAIN,
    FUEL_MAP,
    MODE_MAP,
    MODEL_100,
    RELOAD_MAP,
    SDS_SENSITIVITY_MAP,
    STATUS_MAP,
    TEMP_SPECIAL_LABELS,
    TEMP_SPECIALS,
    model_supports_t2,
)
from .coordinator import TimNetCoordinator


@dataclass(frozen=True, kw_only=True)
class TimNetSensorDescription(SensorEntityDescription):
    """TimNet sensor description."""

    value_fn: Callable[[dict[str, Any]], Any]
    icon_fn: Callable[[dict[str, Any]], str] | None = None
    requires_t2: bool = False
    diagnostic_duplicate: bool = False


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


def _temp_from_key(key: str) -> Callable[[dict[str, Any]], float | str | None]:
    def _temp_value(data: dict[str, Any]) -> float | str | None:
        raw = data.get(key)
        if raw is None:
            return None
        if raw in TEMP_SPECIALS:
            return TEMP_SPECIAL_LABELS[raw]
        return round(raw * 0.1, 1)

    return _temp_value


def _colour_icon(data: dict[str, Any]) -> str:
    colour = COLOUR_MAP.get(data.get("colour"), "none")
    return {
        "none": "mdi:circle-outline",
        "yellow": "mdi:circle",
        "green": "mdi:circle",
        "red": "mdi:circle",
    }.get(colour, "mdi:palette")


def _fault_icon(data: dict[str, Any]) -> str:
    if int(data.get("fault") or 0) == 0:
        return "mdi:check-circle-outline"
    return "mdi:alert"


def _status_icon(data: dict[str, Any]) -> str:
    status = STATUS_MAP.get(data.get("status"), "unknown")
    return {
        "power_start": "mdi:power",
        "idle_100": "mdi:valve-open",
        "idle_0": "mdi:valve-closed",
        "lighting": "mdi:fire",
        "start_regulation": "mdi:play-circle",
        "burning_rising": "mdi:fire",
        "burning_falling": "mdi:fire-off",
        "reload": "mdi:plus-box",
        "ember": "mdi:fire",
        "not_lit": "mdi:fireplace-off",
        "overheated": "mdi:thermometer-alert",
        "door_open_long": "mdi:door-open",
        "test_mode": "mdi:test-tube",
        "temp_fault": "mdi:thermometer-alert",
    }.get(status, "mdi:information-outline")


SENSORS: tuple[TimNetSensorDescription, ...] = (
    TimNetSensorDescription(
        key="temperature_t1",
        translation_key="temperature_t1",
        value_fn=_temp_from_key("t1_raw"),
        icon="mdi:thermometer",
    ),
    TimNetSensorDescription(
        key="temperature_t2",
        translation_key="temperature_t2",
        value_fn=_temp_from_key("t2_raw"),
        icon="mdi:thermometer-water",
        requires_t2=True,
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
        key="mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(MODE_MAP.values()),
        value_fn=lambda d: MODE_MAP.get(d.get("mode"), "unknown"),
        icon="mdi:fire",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        diagnostic_duplicate=True,
    ),
    TimNetSensorDescription(
        key="fuel",
        translation_key="fuel",
        device_class=SensorDeviceClass.ENUM,
        options=list(FUEL_MAP.values()),
        value_fn=lambda d: FUEL_MAP.get(d.get("fuel"), "unknown"),
        icon="mdi:pine-tree",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        diagnostic_duplicate=True,
    ),
    TimNetSensorDescription(
        key="reload_offset",
        translation_key="reload_offset",
        device_class=SensorDeviceClass.ENUM,
        options=list(RELOAD_MAP.values()),
        value_fn=lambda d: RELOAD_MAP.get(d.get("reload"), "unknown"),
        icon="mdi:plus-minus-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        diagnostic_duplicate=True,
    ),
    TimNetSensorDescription(
        key="sds",
        translation_key="sds",
        value_fn=_sds_value,
        icon="mdi:tune-vertical",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        diagnostic_duplicate=True,
    ),
    TimNetSensorDescription(
        key="temperature_colour",
        translation_key="temperature_colour",
        device_class=SensorDeviceClass.ENUM,
        options=list(COLOUR_MAP.values()),
        value_fn=lambda d: COLOUR_MAP.get(d.get("colour"), "unknown"),
        icon="mdi:palette",
        icon_fn=_colour_icon,
    ),
    TimNetSensorDescription(
        key="fault",
        translation_key="fault",
        value_fn=_fault_value,
        icon="mdi:alert",
        icon_fn=_fault_icon,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    TimNetSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=list(STATUS_MAP.values()),
        value_fn=lambda d: STATUS_MAP.get(d.get("status"), "unknown"),
        icon="mdi:information-outline",
        icon_fn=_status_icon,
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
    model = entry.data.get(CONF_MODEL, MODEL_100)
    t2_name = (entry.options.get(CONF_T2_NAME) or "").strip() or None

    entities: list[TimNetSensor] = []
    for desc in SENSORS:
        if desc.requires_t2 and not model_supports_t2(model):
            continue
        entities.append(
            TimNetSensor(
                coordinator,
                device_info,
                device_unique_id,
                desc,
                name_override=t2_name if desc.key == "temperature_t2" else None,
            )
        )
    async_add_entities(entities)


class TimNetSensor(CoordinatorEntity[TimNetCoordinator], SensorEntity):
    """TimNet sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TimNetCoordinator,
        device_info: dict,
        device_unique_id: str,
        description: TimNetSensorDescription,
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
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def icon(self) -> str | None:
        desc = self.entity_description
        if desc.icon_fn and self.coordinator.data:
            return desc.icon_fn(self.coordinator.data)
        return desc.icon

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Unit only when temperature is numeric."""
        key = self.entity_description.key
        if key in ("temperature_t1", "temperature_t2"):
            raw_key = "t1_raw" if key == "temperature_t1" else "t2_raw"
            raw = (self.coordinator.data or {}).get(raw_key)
            if raw in TEMP_SPECIALS or raw is None:
                return None
            return UnitOfTemperature.CELSIUS
        if key == "damper_position":
            val = (self.coordinator.data or {}).get("damper")
            if val == DAMPER_INIT:
                return None
            return PERCENTAGE
        return self.entity_description.native_unit_of_measurement

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Device class only for numeric temperature."""
        key = self.entity_description.key
        if key in ("temperature_t1", "temperature_t2"):
            raw_key = "t1_raw" if key == "temperature_t1" else "t2_raw"
            raw = (self.coordinator.data or {}).get(raw_key)
            if raw in TEMP_SPECIALS or raw is None:
                return None
            return SensorDeviceClass.TEMPERATURE
        return self.entity_description.device_class

    @property
    def state_class(self) -> SensorStateClass | None:
        key = self.entity_description.key
        if key in ("temperature_t1", "temperature_t2"):
            raw_key = "t1_raw" if key == "temperature_t1" else "t2_raw"
            raw = (self.coordinator.data or {}).get(raw_key)
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
