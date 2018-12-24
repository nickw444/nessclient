import asyncio
import logging
import socket
from abc import ABC, abstractmethod
from asyncio import StreamReader, StreamReaderProtocol, StreamWriter
from typing import Optional

LOGGER = logging.getLogger(__name__)


class Connection(ABC):
    """Represents a connection to a Ness D8X/D16X server"""

    @abstractmethod
    async def read(self) -> Optional[bytes]:
        raise NotImplementedError()

    @abstractmethod
    async def write(self, data: bytes) -> None:
        raise NotImplementedError()

    @abstractmethod
    def close(self) -> None:
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
        self._reader, self._writer = await self.open_connection(
            host=self._host,
            port=self._port,
        )
        return True

    async def open_connection(self, host: str, port: int):
        """
        Opens a connection to the remote host.

        Code copied from asyncio.open_connection and modified to support
        enabling TCP socket keepalive.
        """
        reader = StreamReader(limit=2 ** 16, loop=self._loop)
        protocol = StreamReaderProtocol(reader, loop=self._loop)
        transport, _ = await self._loop.create_connection(
            lambda: protocol, host, port)
        s: Optional[socket.socket] = transport.get_extra_info('socket')
        if s is not None:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        writer = StreamWriter(transport, protocol, reader, self._loop)
        return reader, writer

    async def read(self) -> Optional[bytes]:
        assert self._reader is not None

        try:
            data = await self._reader.readuntil(b'\n')
        except asyncio.IncompleteReadError as e:
            LOGGER.warning(
                "Got exception: %s. Most likely the other side has "
                "disconnected!", e)
            self._writer = None
            self._reader = None
            return None

        if data is None:
            LOGGER.warning("Empty response received")
            self._writer = None
            self._reader = None
            return None

        return data.strip()

    async def write(self, data: bytes) -> None:
        assert self._writer is not None

        self._writer.write(data)
        await self._writer.drain()

    def close(self) -> None:
        if self.connected and self._writer is not None:
            self._writer.close()
            self._writer = None
            self._reader = None
