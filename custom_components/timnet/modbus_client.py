"""Async Modbus TCP client for TimNet."""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

_LOGGER = logging.getLogger(__name__)

CONNECTION_TIMEOUT = 5
EXECUTOR_TIMEOUT = 10.0


class TimNetModbusClient:
    """Thin async wrapper around ModbusTcpClient."""

    def __init__(self, host: str, port: int, slave_id: int) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._client: Optional[ModbusTcpClient] = None
        self._lock = asyncio.Lock()
        self._connected = False

    def _create_client(self) -> ModbusTcpClient:
        client = ModbusTcpClient(
            host=self._host,
            port=self._port,
            timeout=CONNECTION_TIMEOUT,
        )
        client.unit_id = self._slave_id
        return client

    async def connect(self) -> bool:
        """Connect to the device."""
        async with self._lock:
            return await self._connect_locked()

    async def _connect_locked(self) -> bool:
        if self._connected and self._client is not None:
            return True

        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass

        self._client = self._create_client()
        loop = asyncio.get_running_loop()
        try:
            ok = await asyncio.wait_for(
                loop.run_in_executor(None, self._client.connect),
                timeout=EXECUTOR_TIMEOUT,
            )
        except (asyncio.TimeoutError, ConnectionException, OSError) as err:
            _LOGGER.debug("TimNet connect failed: %s", err)
            self._connected = False
            return False

        self._connected = bool(ok)
        return self._connected

    async def disconnect(self) -> None:
        """Close the connection."""
        async with self._lock:
            self._connected = False
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:  # noqa: BLE001
                    pass
                self._client = None

    def _read_holding_sync(self, address: int, count: int):
        assert self._client is not None
        try:
            return self._client.read_holding_registers(address, count=count)
        except TypeError:
            return self._client.read_holding_registers(address, count)

    def _write_register_sync(self, address: int, value: int):
        assert self._client is not None
        try:
            return self._client.write_register(address, value)
        except TypeError:
            return self._client.write_register(address, value, slave=self._slave_id)

    async def read_holding_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Read holding registers; returns list of ints or None on failure."""
        async with self._lock:
            if not self._connected and not await self._connect_locked():
                return None
            assert self._client is not None
            loop = asyncio.get_running_loop()
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, lambda: self._read_holding_sync(address, count)
                    ),
                    timeout=EXECUTOR_TIMEOUT,
                )
            except (asyncio.TimeoutError, ConnectionException, ModbusException, OSError) as err:
                _LOGGER.debug("TimNet read failed @%s: %s", address, err)
                self._connected = False
                return None

            if result is None or result.isError():
                _LOGGER.debug("TimNet read error response @%s: %s", address, result)
                self._connected = False
                return None

            regs = list(result.registers)
            # Convert unsigned 16-bit to signed for temperature range
            signed: List[int] = []
            for r in regs:
                if r > 32767:
                    signed.append(r - 65536)
                else:
                    signed.append(r)
            return signed

    async def write_register(self, address: int, value: int) -> bool:
        """Write a single holding register (FC 0x06)."""
        async with self._lock:
            if not self._connected and not await self._connect_locked():
                return False
            assert self._client is not None
            loop = asyncio.get_running_loop()
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, lambda: self._write_register_sync(address, value)
                    ),
                    timeout=EXECUTOR_TIMEOUT,
                )
            except (asyncio.TimeoutError, ConnectionException, ModbusException, OSError) as err:
                _LOGGER.debug("TimNet write failed @%s: %s", address, err)
                self._connected = False
                return False

            if result is None or result.isError():
                _LOGGER.debug("TimNet write error @%s: %s", address, result)
                self._connected = False
                return False
            return True
