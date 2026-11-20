import asyncio
import logging
from abc import ABC, abstractmethod

from serialx import Parity, SerialException, StopBits, open_serial_connection, redact_uri

_LOGGER = logging.getLogger(__name__)

# Bound the wait for a transport to report closure so shutdown always completes
CLOSE_TIMEOUT = 5.0


class Connection(ABC):
    """Represents a connection to a Ness D8X/D16X server"""

    @abstractmethod
    async def read(self) -> bytes | None:
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


class AsyncIoConnection(Connection, ABC):
    """A connection to a Ness D8X/D16X server using asyncio streams.

    The connection owns its reader and writer. They are only released by
    `close()`, which is also called when a read fails, so the underlying
    transport (and, for serial ports, the port itself) is never left open
    without a reference that can close it.
    """

    def __init__(self) -> None:
        super().__init__()

        self._write_lock = asyncio.Lock()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    @property
    def connected(self) -> bool:
        return (
            self._reader is not None
            and self._writer is not None
            and not self._writer.is_closing()
        )

    @abstractmethod
    async def _open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open the underlying transport."""

    async def connect(self) -> bool:
        # Release anything left over from a previous session before opening a
        # new one, a serial port can only be held once.
        await self.close()
        self._reader, self._writer = await self._open()
        return True

    async def read(self) -> bytes | None:
        reader = self._reader
        if reader is None:
            return None

        try:
            try:
                data = await reader.readuntil(b"\n")
            except asyncio.LimitOverrunError as e:
                # A long run of bytes without a line terminator, typically line
                # noise or a wrong serial setting. Discard it and keep reading.
                _LOGGER.warning(
                    "Discarding %d bytes without a line terminator", e.consumed
                )
                await reader.readexactly(e.consumed)
                return b""
        except (asyncio.IncompleteReadError, OSError, SerialException) as e:
            _LOGGER.info("Connection lost: %s", str(e) or type(e).__name__)
            # Only release the session this read belonged to
            if self._reader is reader:
                await self.close()
            return None

        return data.strip()

    async def write(self, data: bytes) -> None:
        async with self._write_lock:
            writer = self._writer
            if writer is None or writer.is_closing():
                raise ConnectionError("Not connected")

            writer.write(data)
            await writer.drain()
            _LOGGER.debug("Wrote %d bytes", len(data))

    async def close(self) -> None:
        writer = self._writer
        self._writer = None
        self._reader = None
        if writer is None:
            return

        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), CLOSE_TIMEOUT)
        except (OSError, SerialException) as e:
            # The transport reports why it closed, which was already handled.
            _LOGGER.debug("Error while closing connection: %s", e)


class IP232Connection(AsyncIoConnection):
    """A connection via IP232 with a Ness D8X/D16X server"""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()

        self._host = host
        self._port = port

    async def _open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        return await asyncio.open_connection(host=self._host, port=self._port)


class Serial232Connection(AsyncIoConnection):
    """A connection via Serial RS232 with a Ness D8X/D16X device or server.

    `tty_path` is any serial port path or URL understood by serialx, such as
    `/dev/ttyUSB0`, `COM3`, or a serial proxy URL.
    """

    def __init__(self, tty_path: str):
        super().__init__()

        self._tty_path = tty_path

    async def _open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        _LOGGER.debug("Opening serial port %s", redact_uri(self._tty_path))
        # The Ness serial interface is always 9600 baud, 8N1, no flow control
        return await open_serial_connection(
            self._tty_path,
            baudrate=9600,
            byte_size=8,
            parity=Parity.NONE,
            stopbits=StopBits.ONE,
            xonxoff=False,
            rtscts=False,
        )
