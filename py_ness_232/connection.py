import asyncio
import logging
from abc import ABC
from typing import Optional

LOGGER = logging.getLogger(__name__)


class Connection(ABC):
    """Represents a connection to a Ness D8X/D16X server"""

    async def read(self) -> Optional[bytes]:
        raise NotImplementedError()

    async def write(self, data: bytes) -> None:
        raise NotImplementedError()

    async def close(self) -> None:
        raise NotImplementedError()

    async def connect(self) -> bool:
        raise NotImplementedError()


class IP232Connection(Connection):
    """A connection via IP232 with a Ness D8X/D16X server"""

    def __init__(self, host: str, port: int, loop: asyncio.AbstractEventLoop = None):
        super().__init__()

        self.__host = host
        self.__port = port
        self.__loop = loop
        self.__reader: asyncio.StreamReader = None
        self.__writer: asyncio.StreamWriter = None

    @property
    def connected(self):
        return self.__reader is not None and self.__writer is not None

    async def connect(self) -> bool:
        self.__reader, self.__writer = await asyncio.open_connection(
            host=self.__host,
            port=self.__port,
            loop=self.__loop
        )
        return True

    async def read(self) -> Optional[bytes]:
        try:
            data = await self.__reader.readuntil(b'\n')
        except asyncio.IncompleteReadError as e:
            LOGGER.warning(
                "Got exception: %s. Most likely the other side has "
                "disconnected!", e)
            self.__writer = None
            self.__reader = None
            return None

        if data is None:
            LOGGER.warning("Empty response received")
            self.__writer = None
            self.__reader = None
            return None

        return data.strip()

    async def write(self, data: bytes) -> None:
        self.__writer.write(data)
        await self.__writer.drain()

    def close(self) -> None:
        if self.connected:
            self.__writer.close()
