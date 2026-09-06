"""Data update coordinator for TimNet."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    READ_COUNT,
    READ_START,
    REG_BARVA,
    REG_BEEP_R,
    REG_CAS,
    REG_INP,
    REG_P_LIFE,
    REG_PALIVO,
    REG_PORUCHA,
    REG_PRILOZ,
    REG_RELE1,
    REG_RELE2,
    REG_REZIM,
    REG_SDS,
    REG_SER1,
    REG_STAT,
    REG_TT,
    REG_TT2,
)
from .modbus_client import TimNetModbusClient

_LOGGER = logging.getLogger(__name__)


class TimNetCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll TimNet holding registers 0–15 as one block."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TimNetModbusClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        regs = await self.client.read_holding_registers(READ_START, READ_COUNT)
        if regs is None or len(regs) < READ_COUNT:
            raise UpdateFailed("Failed to read TimNet registers")

        return {
            "t1_raw": regs[REG_TT],
            "t2_raw": regs[REG_TT2],
            "burn_seconds": regs[REG_CAS],
            "damper": regs[REG_SER1],
            "door": regs[REG_INP],
            "mode": regs[REG_REZIM],
            "fuel": regs[REG_PALIVO],
            "reload": regs[REG_PRILOZ],
            "sds": regs[REG_SDS],
            "colour": regs[REG_BARVA],
            "beep": regs[REG_BEEP_R],
            "rele1": regs[REG_RELE1],
            "rele2": regs[REG_RELE2],
            "fault": regs[REG_PORUCHA],
            "status": regs[REG_STAT],
            "reload_count": regs[REG_P_LIFE],
            "raw": regs,
        }
