"""The TimNet combustion control integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    MANUFACTURER,
    MODEL_100,
    PLATFORMS,
    REG_START_W,
    SERVICE_START_REGULATION,
    WRITE_START,
)
from .coordinator import TimNetCoordinator
from .modbus_client import TimNetModbusClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TimNet from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = int(entry.data.get(CONF_PORT, 502))
    slave_id = int(entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID))
    name = entry.data.get(CONF_NAME, "TimNet")
    scan_interval = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    client = TimNetModbusClient(host, port, slave_id)
    if not await client.connect():
        await client.disconnect()
        raise ConfigEntryNotReady(f"Cannot connect to TimNet at {host}:{port}")

    coordinator = TimNetCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    device_unique_id = f"{host}_{port}_{slave_id}"
    device_info = {
        "identifiers": {(DOMAIN, device_unique_id)},
        "name": name,
        "manufacturer": MANUFACTURER,
        "model": MODEL_100,
    }

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        **device_info,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "device_info": device_info,
        "device_unique_id": device_unique_id,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_START_REGULATION):

        async def async_handle_start_regulation(call: ServiceCall) -> None:
            """Write START register to begin regulation / burning."""
            entry_id = call.data.get("entry_id")
            store = hass.data.get(DOMAIN, {})
            if entry_id:
                data = store.get(entry_id)
            elif len(store) == 1:
                data = next(iter(store.values()))
            else:
                raise HomeAssistantError(
                    "Specify entry_id when multiple TimNet devices are configured"
                )
            if not data:
                raise HomeAssistantError("TimNet entry not found")
            ok = await data["client"].write_register(REG_START_W, WRITE_START)
            if not ok:
                raise HomeAssistantError("Failed to write TimNet START register")
            await data["coordinator"].async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            SERVICE_START_REGULATION,
            async_handle_start_regulation,
        )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data:
            await data["client"].disconnect()
        if not hass.data[DOMAIN]:
            if hass.services.has_service(DOMAIN, SERVICE_START_REGULATION):
                hass.services.async_remove(DOMAIN, SERVICE_START_REGULATION)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
