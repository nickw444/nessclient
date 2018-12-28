import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class Connection(ABC):
    """Represents a connection to a Ness D8X/D16X server"""

    @abstractmethod
    async def read(self) -> Optional[bytes]:
        raise NotImplementedError()

    @abstractmethod
    async def write(self, data: bytes) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def connect(self) -> bool:
        raise NotImplementedError()

    @property
    @abstractmethod
    def connected(self) -> bool:
        raise NotImplementedError()


class IP232Connection(Connection):
    """A connection via IP232 with a Ness D8X/D16X server"""

    def __init__(self, host: str, port: int,
                 loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()):
        super().__init__()

        self._host = host
        self._port = port
        self._loop = loop
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    @property
    def connected(self) -> bool:
        return self._reader is not None and self._writer is not None

    async def connect(self) -> bool:
        self._reader, self._writer = await asyncio.open_connection(
            host=self._host,
            port=self._port,
            loop=self._loop,
        )
        return True

    async def read(self) -> Optional[bytes]:
        assert self._reader is not None

        try:
            data = await self._reader.readuntil(b'\n')
        except (asyncio.IncompleteReadError, TimeoutError,
                ConnectionResetError) as e:
            _LOGGER.info(
                "Got exception: %s. Most likely the other side has "
                "disconnected!", e)
            self._writer = None
            self._reader = None
            return None

        if data is None:
            _LOGGER.info("Empty response received")
            self._writer = None
            self._reader = None
            return None

        return data.strip()

    async def write(self, data: bytes) -> None:
        assert self._writer is not None

        self._writer.write(data)
        await self._writer.drain()

    async def close(self) -> None:
        if self.connected and self._writer is not None:
            self._writer.close()
            if hasattr(self._writer, 'wait_closed'):
                await self._writer.wait_closed()  # type: ignore
            self._writer = None
            self._reader = None
