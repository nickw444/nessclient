from __future__ import annotations

from typing import TextIO

from ..connection import Connection


class LoggingConnection(Connection):
    """Wrap a connection and log raw packet ASCII data."""

    def __init__(self, inner: Connection, log_file: TextIO) -> None:
        self._inner = inner
        self._log_file = log_file

    @property
    def connected(self) -> bool:
        return self._inner.connected

    async def connect(self) -> bool:
        return await self._inner.connect()

    async def close(self) -> None:
        await self._inner.close()

    async def read(self) -> bytes | None:
        data = await self._inner.read()
        if data is not None:
            try:
                self._log_file.write(f"RX {data.decode('ascii').strip()}\n")
                self._log_file.flush()
            except Exception:
                pass
        return data

    async def write(self, data: bytes) -> None:
        try:
            self._log_file.write(f"TX {data.decode('ascii').strip()}\n")
            self._log_file.flush()
        except Exception:
            pass
        await self._inner.write(data)
