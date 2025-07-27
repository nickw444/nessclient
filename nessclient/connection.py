"""Provides classes for connections between a nessclient and a Ness alarm device."""

import asyncio
import logging
from abc import ABC, abstractmethod
import serial
from serial_asyncio_fast import SerialTransport, create_serial_connection

_LOGGER = logging.getLogger(__name__)


class Connection(ABC):
    """Represents an abstract asynchronous connection to a Ness D8X/D16X server."""

    @abstractmethod
    async def read(self) -> bytes | None:
        r"""
        Read bytes from the connection until a newline '\n' is received.

        :return: The bytes received - or None if an error occurred
        """
        raise NotImplementedError()

    @abstractmethod
    async def write(self, data: bytes) -> None:
        """
        Write bytes to the connection.

        :param data: The bytes to be written
        """
        raise NotImplementedError()

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        raise NotImplementedError()

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish the conection.

        :return: True if the connection was successfully established
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def connected(self) -> bool:
        """
        Indicates whether the conection is currently connected.

        :return: True if the connection is connected
        """
        raise NotImplementedError()


class AsyncIoConnection(Connection, ABC):
    """
    Abstract connection based on asyncio.

    An abstract connection via asyncio with an :py:class:`asyncio.StreamReader`
    and :py:class:`asyncio.StreamReader` with a Ness D8X/D16X server

    Note: Subclasses must override:
          1) The constructor to capture the appropriate details of the connection
          2) The connect method
    """

    def __init__(self) -> None:
        """Construct a AsyncIoConnection object."""
        super().__init__()

        self._write_lock = asyncio.Lock()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    @property
    def connected(self) -> bool:
        """
        Indicate whether the conection is currently connected.

        :return: True if the connection is connected
        """
        return self._reader is not None and self._writer is not None

    async def read(self) -> bytes | None:
        r"""
        Read bytes from the connection until a newline '\n' is received.

        :return: The bytes received - or None if an error occurred
        """
        assert self._reader is not None

        try:
            data = await self._reader.readuntil(b"\n")
        except (asyncio.IncompleteReadError, TimeoutError, ConnectionResetError) as e:
            _LOGGER.info(
                "Got exception: %s. Most likely the other side has disconnected!", e
            )
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
        """
        Write bytes to the connection.

        :param data: The bytes to be written
        """
        _LOGGER.debug("Waiting for write_lock to write data: %s", data)
        async with self._write_lock:
            _LOGGER.debug("Obtained write_lock to write data: %s", data)
            assert self._writer is not None

            self._writer.write(data)
            await self._writer.drain()
            _LOGGER.debug("Data was written: %s", data)

    async def close(self) -> None:
        """Close the connection."""
        if self.connected and self._writer is not None:
            self._writer.close()
            if hasattr(self._writer, "wait_closed"):
                await self._writer.wait_closed()
            self._writer = None
            self._reader = None


class IP232Connection(AsyncIoConnection):
    """
    A TCP asyncio connection.

    A TCP connection to a host & port - e.g. via a IP232 with
    a Ness D8X/D16X alarm device or simulated-device-server
    """

    def __init__(self, host: str, port: int) -> None:
        """
        Construct and initialises the IP232Connection object.

        :param host: The TCP host name of the Ness D8X/D16X alarm
                     device or simulated-device-server
        :param port: The TCP port number of the Ness D8X/D16X alarm
                     device or simulated-device-server
        """
        super().__init__()

        self._host = host
        self._port = port

    async def connect(self) -> bool:
        """
        Establish the conection.

        :return: True if the connection was successfully established
        """
        self._reader, self._writer = await asyncio.open_connection(
            host=self._host,
            port=self._port,
        )
        return True


class Serial232Connection(AsyncIoConnection):
    """
    A serial connection.

    A connection via Serial RS232 with a Ness D8X/D16X alarm
    device or simulated-device-server
    """

    def __init__(self, tty_path: str) -> None:
        """
        Construct and initialises the Serial232Connection object.

        :param tty_path: The path to the serial port to be used
        """
        super().__init__()

        self._tty_path = tty_path
        self._serial_connection: serial.Serial | None = None

    @property
    def connected(self) -> bool:
        """
        Indicate whether the serial conection is currently connected.

        :return: True if the connection is connected
        """
        return (
            super().connected
            and self._serial_connection is not None
            and self._serial_connection.isOpen()
        )

    async def connect(self) -> bool:
        """
        Establish the serial conection.

        Note: Ness serial port is always set to 9600 baud and N-8-1

        :return: True if the connection was successfully established
        """
        loop = asyncio.get_event_loop()
        self._reader = asyncio.StreamReader(loop=loop)
        protocol_in = asyncio.StreamReaderProtocol(self._reader, loop=loop)
        transport: SerialTransport

        # Open the serial connection - always 9600 baud N-8-1
        transport, protocol = await create_serial_connection(
            loop,
            lambda: protocol_in,
            self._tty_path,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
        )
        self._serial_connection = transport.serial
        self._writer = asyncio.StreamWriter(transport, protocol, self._reader, loop)

        return self._serial_connection is not None and self._serial_connection.isOpen()
