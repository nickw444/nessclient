import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from serialx import Parity, StopBits

from nessclient.connection import AsyncIoConnection, IP232Connection, Serial232Connection

from .fake_panel import FakePanel, encode_command, status_response


class StreamConnection(AsyncIoConnection):
    """Connection backed by an in-memory reader, to test stream handling."""

    def __init__(self, limit: int = 2**16) -> None:
        super().__init__()
        self.opened = 0
        self.writers: list[Mock] = []
        self.limit = limit
        self.reader = asyncio.StreamReader(limit=limit)

    async def _open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        self.opened += 1
        self.reader = asyncio.StreamReader(limit=self.limit)
        writer = Mock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.wait_closed = AsyncMock()
        self.writers.append(writer)
        return self.reader, writer


@pytest.mark.parametrize(
    "path",
    [
        "/dev/ttyUSB0",
        "COM3",
        "esphome-hass://esphome/01JEXAMPLE?port_name=RS232%201",
    ],
)
@pytest.mark.asyncio
async def test_serial_connection_opens_port_with_ness_settings(path: str) -> None:
    reader = asyncio.StreamReader()
    writer = Mock(spec=asyncio.StreamWriter)
    writer.is_closing.return_value = False
    with patch(
        "nessclient.connection.open_serial_connection",
        AsyncMock(return_value=(reader, writer)),
    ) as open_serial:
        connection = Serial232Connection(tty_path=path)
        assert await connection.connect() is True

    open_serial.assert_awaited_once_with(
        path,
        baudrate=9600,
        byte_size=8,
        parity=Parity.NONE,
        stopbits=StopBits.ONE,
        xonxoff=False,
        rtscts=False,
    )
    assert connection.connected


@pytest.mark.asyncio
async def test_serial_connection_through_serialx_backend() -> None:
    """Exchange data through serialx's socket:// backend (simulated port)."""
    async with FakePanel() as panel:
        connection = Serial232Connection(tty_path=panel.serial_url)
        await connection.connect()
        await connection.write(encode_command("S14"))
        assert await connection.read() == status_response("14").strip()

        await connection.close()
        await panel.wait_for_connections(0)
        assert not connection.connected


@pytest.mark.asyncio
async def test_ip232_connection_round_trip() -> None:
    async with FakePanel() as panel:
        connection = IP232Connection(host="127.0.0.1", port=panel.port)
        await connection.connect()
        await connection.write(encode_command("S14"))
        assert await connection.read() == status_response("14").strip()

        await connection.close()
        await panel.wait_for_connections(0)


@pytest.mark.asyncio
async def test_read_assembles_fragmented_frames() -> None:
    connection = StreamConnection()
    await connection.connect()

    connection.reader.feed_data(b"8200036014")
    read = asyncio.create_task(connection.read())
    await asyncio.sleep(0)
    assert not read.done()

    connection.reader.feed_data(b"0000xx\r\n")
    assert await read == b"82000360140000xx"


@pytest.mark.asyncio
async def test_read_separates_combined_frames() -> None:
    connection = StreamConnection()
    await connection.connect()

    connection.reader.feed_data(b"first\r\nsecond\r\n")
    assert await connection.read() == b"first"
    assert await connection.read() == b"second"


@pytest.mark.asyncio
async def test_read_discards_overlong_garbage() -> None:
    connection = StreamConnection(limit=16)
    await connection.connect()

    connection.reader.feed_data(b"x" * 40)
    assert await connection.read() == b""
    assert connection.connected

    connection.reader.feed_data(b"\r\nvalid\r\n")
    assert await connection.read() == b""
    assert await connection.read() == b"valid"


@pytest.mark.asyncio
async def test_failed_read_releases_transport() -> None:
    connection = StreamConnection()
    await connection.connect()
    writer = connection.writers[0]

    connection.reader.feed_eof()
    assert await connection.read() is None

    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()
    assert not connection.connected
    # Closing again is safe and does not touch the released writer
    await connection.close()
    writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_read_error_from_transport_releases_transport() -> None:
    connection = StreamConnection()
    await connection.connect()
    writer = connection.writers[0]

    connection.reader.set_exception(ConnectionResetError("proxy went away"))
    assert await connection.read() is None
    writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_releases_transport_when_already_closing() -> None:
    connection = StreamConnection()
    await connection.connect()
    writer = connection.writers[0]
    writer.is_closing.return_value = True
    writer.wait_closed.side_effect = ConnectionResetError("closed with error")

    assert not connection.connected
    await connection.close()

    writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_connect_releases_previous_transport() -> None:
    connection = StreamConnection()
    await connection.connect()
    await connection.connect()

    assert connection.opened == 2
    connection.writers[0].close.assert_called_once()
    connection.writers[1].close.assert_not_called()


@pytest.mark.asyncio
async def test_write_without_connection_raises() -> None:
    connection = StreamConnection()
    with pytest.raises(ConnectionError):
        await connection.write(b"data")


@pytest.mark.asyncio
async def test_writes_are_serialized() -> None:
    connection = StreamConnection()
    await connection.connect()
    writer = connection.writers[0]
    drained = asyncio.Event()
    order: list[str] = []

    async def drain() -> None:
        order.append("drain")
        await drained.wait()

    writer.drain.side_effect = drain
    writer.write.side_effect = lambda data: order.append(data.decode())

    first = asyncio.create_task(connection.write(b"one"))
    second = asyncio.create_task(connection.write(b"two"))
    await asyncio.sleep(0.01)
    assert order == ["one", "drain"]

    drained.set()
    await asyncio.gather(first, second)
    assert order == ["one", "drain", "two", "drain"]
