"""Connection lifecycle tests against a simulated panel.

The simulated panel is reached over IP232 and through serialx's socket://
backend (standing in for a serial port or serial proxy).
"""

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from nessclient import Client, ClientClosedError, PanelNotRespondingError
from nessclient.alarm import ArmingState
from nessclient.connection import Connection
from nessclient.event import ArmingUpdate

from .fake_panel import ZONE_3_UNSEALED, FakePanel, status_response


def ip232_client(panel: FakePanel, **kwargs: float) -> Client:
    return Client(host="127.0.0.1", port=panel.port, **kwargs)  # type: ignore[arg-type]


def serial_client(panel: FakePanel, **kwargs: float) -> Client:
    return Client(serial_tty=panel.serial_url, **kwargs)  # type: ignore[arg-type]


async def unused_port() -> int:
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port: int = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()
    return port


class BlockingConnection(Connection):
    """Connection whose connect() waits until released by the test."""

    def __init__(self) -> None:
        self.connect_started = asyncio.Event()
        self.release_connect = asyncio.Event()
        self.is_open = False
        self.close_calls = 0

    @property
    def connected(self) -> bool:
        return self.is_open

    async def connect(self) -> bool:
        self.connect_started.set()
        await self.release_connect.wait()
        self.is_open = True
        return True

    async def close(self) -> None:
        self.close_calls += 1
        self.is_open = False

    async def read(self) -> bytes | None:
        await asyncio.Event().wait()
        return None

    async def write(self, data: bytes) -> None:
        pass


@pytest.mark.parametrize("make_client", [ip232_client, serial_client])
@pytest.mark.asyncio
async def test_probe_succeeds_with_matching_response(make_client) -> None:
    async with FakePanel() as panel:
        client = make_client(panel)
        response = await client.probe(timeout=2)

        assert isinstance(response, ArmingUpdate)
        assert client.available
        assert client.alarm.arming_state == ArmingState.DISARMED
        assert panel.received == ["S14"]

        await client.close()
        await panel.wait_for_connections(0)


@pytest.mark.parametrize("make_client", [ip232_client, serial_client])
@pytest.mark.asyncio
async def test_probe_silent_panel_raises_and_releases(make_client) -> None:
    async with FakePanel() as panel:
        panel.answer_status_requests = False
        client = make_client(panel)

        with pytest.raises(PanelNotRespondingError):
            await client.probe(timeout=0.3)
        assert not client.available

        await client.close()
        await panel.wait_for_connections(0)


@pytest.mark.asyncio
async def test_probe_ignores_unrelated_invalid_and_nonmatching_data() -> None:
    async with FakePanel() as panel:
        panel.answer_status_requests = False
        client = serial_client(panel)
        probe = asyncio.create_task(client.probe(timeout=2))
        await panel.wait_for_request("S14")

        await panel.send(status_response("00"))
        await panel.send(ZONE_3_UNSEALED)
        await panel.send(b"not a ness packet\r\n")
        await panel.send(b"\xff\xfe\r\n")
        await asyncio.sleep(0.05)
        assert not probe.done()

        # A valid matching response, split across two reads
        response = status_response("14")
        await panel.send(response[:7])
        await asyncio.sleep(0.05)
        assert not probe.done()
        await panel.send(response[7:])

        assert isinstance(await probe, ArmingUpdate)
        assert client.alarm.zones[2].triggered is True
        await client.close()


@pytest.mark.asyncio
async def test_probe_connection_refused_raises_oserror() -> None:
    client = Client(host="127.0.0.1", port=await unused_port())

    with pytest.raises(OSError) as err:
        await client.probe(timeout=2)
    assert not isinstance(err.value, PanelNotRespondingError)

    await client.close()
    await client.close()


@pytest.mark.asyncio
async def test_probe_recovers_after_correction() -> None:
    async with FakePanel() as panel:
        panel.answer_status_requests = False
        first = serial_client(panel)
        with pytest.raises(PanelNotRespondingError):
            await first.probe(timeout=0.2)
        await first.close()

        panel.answer_status_requests = True
        second = serial_client(panel)
        await second.probe(timeout=2)
        await second.close()
        await panel.wait_for_connections(0)


@pytest.mark.asyncio
async def test_probe_cancellation_releases_resources() -> None:
    async with FakePanel() as panel:
        panel.answer_status_requests = False
        client = serial_client(panel)
        probe = asyncio.create_task(client.probe(timeout=5))
        await panel.wait_for_request("S14")

        probe.cancel()
        with pytest.raises(asyncio.CancelledError):
            await probe
        await client.close()

        await panel.wait_for_connections(0)


@pytest.mark.asyncio
async def test_probe_on_running_client_uses_existing_connection() -> None:
    async with FakePanel() as panel:
        client = serial_client(panel)
        await client.probe(timeout=2)
        keepalive = asyncio.create_task(client.keepalive())

        await client.probe(timeout=2)
        assert panel.connection_count == 1

        await client.close()
        await keepalive


@pytest.mark.asyncio
async def test_keepalive_reconnects_and_refreshes_after_disconnect() -> None:
    async with FakePanel() as panel:
        client = serial_client(panel)
        changes: list[bool] = []
        client.on_availability_change(changes.append)
        await client.probe(timeout=2)
        keepalive = asyncio.create_task(client.keepalive())

        # The first refresh requests full state
        await panel.wait_for_request("S00")
        panel.received.clear()

        await panel.drop_connections()
        async with asyncio.timeout(3):
            while changes[-1:] != [True] or len(changes) < 3:
                await asyncio.sleep(0.01)

        assert changes == [True, False, True]
        assert panel.connection_count == 2
        # Fresh state was requested on the new session before recovering
        assert panel.received[:4] == ["S00", "S20", "S18", "S14"]

        await client.close()
        assert await keepalive is None
        await panel.wait_for_connections(0)


@pytest.mark.asyncio
async def test_refresh_waits_for_responses_and_skips_unsupported_reports() -> None:
    async with FakePanel() as panel:
        client = serial_client(panel, response_timeout=0.5)
        await client.probe(timeout=2)
        panel.received.clear()
        panel.answer_status_requests = False
        keepalive = asyncio.create_task(client.keepalive())
        try:
            await panel.wait_for_request("S00")
            with pytest.raises(TimeoutError):
                await panel.wait_for_request("S20", timeout=0.05)
            await panel.send(status_response("00"))
            await panel.wait_for_request("S20")
            # Simulate a panel without the extended zone report.
            await panel.wait_for_request("S18")
            await panel.send(status_response("18"))
            await panel.wait_for_request("S14")
            await panel.send(status_response("14"))
            assert panel.received == ["S00", "S20", "S18", "S14"]
        finally:
            await client.close()
            await keepalive


@pytest.mark.asyncio
async def test_keepalive_detects_panel_that_stops_answering() -> None:
    async with FakePanel() as panel:
        client = serial_client(panel, update_interval=0.2, response_timeout=0.1)
        changes: list[bool] = []
        client.on_availability_change(changes.append)
        await client.probe(timeout=2)
        keepalive = asyncio.create_task(client.keepalive())

        # Proxy still connected, but the serial link to the panel is broken
        panel.answer_status_requests = False
        async with asyncio.timeout(3):
            while changes[-1] is not False:
                await asyncio.sleep(0.01)

        panel.answer_status_requests = True
        async with asyncio.timeout(3):
            while changes[-1] is not True:
                await asyncio.sleep(0.01)

        assert changes == [True, False, True]
        await client.close()
        await keepalive


@pytest.mark.asyncio
async def test_pending_request_fails_when_connection_is_lost() -> None:
    async with FakePanel() as panel:
        client = serial_client(panel)
        await client.probe(timeout=2)
        keepalive = asyncio.create_task(client.keepalive())
        await panel.wait_for_request("S00")

        panel.answer_status_requests = False
        request = asyncio.create_task(client.send_command_and_wait("S17", timeout=5))
        await panel.wait_for_request("S17")
        await panel.drop_connections()

        with pytest.raises(ConnectionError):
            await request
        assert client._pending_ui_requests == {}

        await client.close()
        await keepalive


@pytest.mark.asyncio
async def test_update_alongside_keepalive_waits_for_connection() -> None:
    """The pattern used by the examples and CLI keeps working."""
    async with FakePanel() as panel:
        client = ip232_client(panel)
        keepalive = asyncio.create_task(client.keepalive())

        await asyncio.wait_for(client.update(), 2)
        await panel.wait_for_request("S18")

        await client.close()
        await keepalive


@pytest.mark.asyncio
async def test_close_during_reconnect_backoff_is_prompt() -> None:
    client = Client(host="127.0.0.1", port=await unused_port())
    keepalive = asyncio.create_task(client.keepalive())
    await asyncio.sleep(0.5)
    assert not keepalive.done()

    async with asyncio.timeout(1):
        await client.close()
        assert await keepalive is None

    with pytest.raises(ClientClosedError):
        await client.send_command("S00")


@pytest.mark.asyncio
async def test_close_while_receive_loop_is_opening() -> None:
    connection = BlockingConnection()
    client = Client(connection=connection)
    keepalive = asyncio.create_task(client.keepalive())
    await connection.connect_started.wait()

    async with asyncio.timeout(1):
        await client.close()
        await keepalive

    assert not connection.connected
    assert connection.close_calls == 1


@pytest.mark.asyncio
async def test_connection_opened_after_close_is_released() -> None:
    connection = BlockingConnection()
    client = Client(connection=connection)
    probe = asyncio.create_task(client.probe(timeout=2))
    await connection.connect_started.wait()

    await client.close()
    connection.release_connect.set()

    with pytest.raises(ClientClosedError):
        await probe
    assert not connection.connected
    assert connection.close_calls == 2


@pytest.mark.asyncio
async def test_closed_client_does_not_reconnect() -> None:
    async with FakePanel() as panel:
        client = serial_client(panel)
        await client.probe(timeout=2)
        await client.close()

        with pytest.raises(ClientClosedError):
            await client.probe(timeout=2)
        with pytest.raises(ClientClosedError):
            await client.arm_away("1234")
        assert panel.connection_count == 1


@pytest.mark.asyncio
async def test_send_command_and_wait_timeout_removes_waiter() -> None:
    client = Client(connection=AsyncMock(Connection))

    with pytest.raises(TimeoutError):
        await client.send_command_and_wait("S14", timeout=0.01)
    assert client._pending_ui_requests == {}


@pytest.mark.asyncio
async def test_commands_do_not_log_user_codes(caplog: pytest.LogCaptureFixture) -> None:
    client = Client(connection=AsyncMock(Connection))
    caplog.set_level(logging.DEBUG)

    await client.disarm("1234")
    await client.arm_away("5678")
    await client.panic("9012")
    await client.send_command("S14")

    for code in ("1234", "5678", "9012"):
        assert code not in caplog.text
    assert "S14" in caplog.text
