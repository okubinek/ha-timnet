"""Config flow for TimNet."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_MODEL,
    CONF_RELAY1_NAME,
    CONF_RELAY2_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_T2_NAME,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    MODEL_100,
    MODELS,
    REG_STAT,
)
from .modbus_client import TimNetModbusClient

_LOGGER = logging.getLogger(__name__)


def _user_schema(
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Build the user / reconfigure schema with optional defaults."""
    d = defaults or {}
    host_field: Any
    if CONF_HOST in d:
        host_field = vol.Required(CONF_HOST, default=d[CONF_HOST])
    else:
        host_field = vol.Required(CONF_HOST)

    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=d.get(CONF_NAME, DEFAULT_NAME)): str,
            host_field: str,
            vol.Required(
                CONF_PORT, default=d.get(CONF_PORT, DEFAULT_PORT)
            ): cv.port,
            vol.Required(
                CONF_SLAVE_ID, default=d.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
            vol.Required(
                CONF_MODEL, default=d.get(CONF_MODEL, MODEL_100)
            ): SelectSelector(
                SelectSelectorConfig(options=list(MODELS))
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=3, max=10)),
        }
    )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate connection by reading status register."""
    client = TimNetModbusClient(
        data[CONF_HOST],
        int(data[CONF_PORT]),
        int(data[CONF_SLAVE_ID]),
    )
    try:
        if not await client.connect():
            raise ConnectionError("connect_failed")
        regs = await client.read_holding_registers(REG_STAT, 1)
        if regs is None:
            raise ConnectionError("read_failed")
    finally:
        await client.disconnect()

    return {"title": data[CONF_NAME]}


class TimNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TimNet."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}_{user_input[CONF_SLAVE_ID]}"
            )
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except ConnectionError as err:
                key = (
                    str(err)
                    if str(err) in ("connect_failed", "read_failed")
                    else "cannot_connect"
                )
                errors["base"] = key
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during TimNet validation")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow changing host / port / unit ID / model without re-adding."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}_{user_input[CONF_SLAVE_ID]}"
            )
            self._abort_if_unique_id_mismatch()

            try:
                await validate_input(self.hass, user_input)
            except ConnectionError as err:
                key = (
                    str(err)
                    if str(err) in ("connect_failed", "read_failed")
                    else "cannot_connect"
                )
                errors["base"] = key
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during TimNet reconfigure")
                errors["base"] = "unknown"
            else:
                scan_interval = user_input.pop(CONF_SCAN_INTERVAL, None)
                new_options = {**entry.options}
                if scan_interval is not None:
                    new_options[CONF_SCAN_INTERVAL] = scan_interval
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    options=new_options,
                )

        defaults = {
            CONF_NAME: entry.data.get(CONF_NAME, DEFAULT_NAME),
            CONF_HOST: entry.data[CONF_HOST],
            CONF_PORT: entry.data.get(CONF_PORT, DEFAULT_PORT),
            CONF_SLAVE_ID: entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID),
            CONF_MODEL: entry.data.get(CONF_MODEL, MODEL_100),
            CONF_SCAN_INTERVAL: entry.options.get(
                CONF_SCAN_INTERVAL,
                entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return TimNetOptionsFlow()


class TimNetOptionsFlow(config_entries.OptionsFlow):
    """Handle TimNet options (poll interval, model labels)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            # Persist model change into entry data so platforms see it after reload
            model = user_input.pop(CONF_MODEL, None)
            if model and model != self.config_entry.data.get(CONF_MODEL):
                new_data = {**self.config_entry.data, CONF_MODEL: model}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_model = self.config_entry.data.get(CONF_MODEL, MODEL_100)
        opts = self.config_entry.options

        schema: dict[Any, Any] = {
            vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                vol.Coerce(int), vol.Range(min=3, max=10)
            ),
            vol.Required(CONF_MODEL, default=current_model): SelectSelector(
                SelectSelectorConfig(options=list(MODELS))
            ),
            vol.Optional(CONF_T2_NAME, default=opts.get(CONF_T2_NAME, "")): str,
            vol.Optional(
                CONF_RELAY1_NAME, default=opts.get(CONF_RELAY1_NAME, "")
            ): str,
            vol.Optional(
                CONF_RELAY2_NAME, default=opts.get(CONF_RELAY2_NAME, "")
            ): str,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )
