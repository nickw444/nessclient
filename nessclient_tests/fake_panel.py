"""Simulated Ness panel for transport tests.

Serves the ASCII protocol over TCP on localhost. Tests reach it either through
IP232 (`host`/`port`) or through serialx's `socket://` backend, which exercises
the same serialx stream path as a serial port or serial proxy. This is a
simulation; it does not replace testing against real hardware.
"""

import asyncio
from types import TracebackType

from nessclient.packet import CommandType, Packet

CRLF = "\r\n"


def status_response(request_id: str, data: str = "0000") -> bytes:
    """Encode a USER_INTERFACE status response for a request id such as '14'."""
    packet = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data=f"{request_id}{data}",
        timestamp=None,
        is_user_interface_resp=True,
    )
    return (packet.encode() + CRLF).encode("ascii")


def encode_command(command: str) -> bytes:
    """Encode a USER_INTERFACE request as the client sends it."""
    packet = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data=command,
        timestamp=None,
    )
    return (packet.encode() + CRLF).encode("ascii")


# Zone 3 unsealed system status event, from the protocol specification
ZONE_3_UNSEALED = b"87020361000301080510234500E5" + CRLF.encode("ascii")


class FakePanel:
    def __init__(self) -> None:
        self.answer_status_requests = True
        self.received: list[str] = []
        self.connection_count = 0
        self._writers: set[asyncio.StreamWriter] = set()
        self._server: asyncio.Server | None = None
        self._request = asyncio.Event()

    @property
    def port(self) -> int:
        assert self._server is not None
        port: int = self._server.sockets[0].getsockname()[1]
        return port

    @property
    def serial_url(self) -> str:
        return f"socket://127.0.0.1:{self.port}"

    @property
    def open_connections(self) -> int:
        return len(self._writers)

    async def __aenter__(self) -> "FakePanel":
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.stop()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
        await self.drop_connections()
        if self._server is not None:
            await self._server.wait_closed()
            self._server = None

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.connection_count += 1
        self._writers.add(writer)
        try:
            while True:
                line = await reader.readuntil(b"\n")
                command = Packet.decode(line.decode("ascii").strip()).data
                self.received.append(command)
                self._request.set()
                if self.answer_status_requests and command.startswith("S"):
                    writer.write(status_response(command[1:3]))
                    await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()

    async def send(self, data: bytes) -> None:
        """Send raw bytes to every connected client."""
        for writer in list(self._writers):
            writer.write(data)
            await writer.drain()

    async def wait_for_request(self, command: str, timeout: float = 2.0) -> None:
        async with asyncio.timeout(timeout):
            while command not in self.received:
                self._request.clear()
                await self._request.wait()

    async def wait_for_connections(self, count: int, timeout: float = 2.0) -> None:
        async with asyncio.timeout(timeout):
            while self.open_connections != count:
                await asyncio.sleep(0.01)

    async def drop_connections(self) -> None:
        for writer in list(self._writers):
            writer.close()
        self._writers.clear()
