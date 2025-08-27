from unittest.mock import Mock, AsyncMock

import pytest

from nessclient import Client
from nessclient.alarm import Alarm, PanelInfo
from nessclient.connection import Connection
from nessclient.event import StatusUpdate, BaseEvent, PanelVersionUpdate
from nessclient.packet import Packet, CommandType
import asyncio


def get_data(pkt: bytes) -> bytes:
    return pkt[7:-4]


def panel_version_response(
    model: PanelVersionUpdate.Model,
    major: int = 8,
    minor: int = 7,
) -> PanelVersionUpdate:
    """Construct a PanelVersionUpdate event for PANEL_VERSION (S17).

    Returns an event instance directly to avoid encode/decode roundtrips.
    """
    return PanelVersionUpdate(
        model=model,
        major_version=major,
        minor_version=minor,
        address=0x00,
        timestamp=None,
    )


@pytest.mark.asyncio
async def test_arm_away(connection, client):
    await client.arm_away("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"A1234E"


@pytest.mark.asyncio
async def test_arm_home(connection, client):
    await client.arm_home("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"H1234E"


@pytest.mark.asyncio
async def test_disarm(connection, client):
    await client.disarm("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"1234E"


@pytest.mark.asyncio
async def test_panic(connection, client):
    await client.panic("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"*1234#"


@pytest.mark.asyncio
async def test_aux_on(connection, client):
    await client.aux(1, True)
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"11*"


@pytest.mark.asyncio
async def test_aux_off(connection, client):
    await client.aux(1, False)
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"11#"


@pytest.mark.asyncio
async def test_update(connection, client: Client, alarm: Alarm):
    # Update should send S00, S20 and S14
    await client.update()
    assert connection.write.call_count == 3
    commands = {
        get_data(connection.write.call_args_list[0][0][0]),
        get_data(connection.write.call_args_list[1][0][0]),
        get_data(connection.write.call_args_list[2][0][0]),
    }
    assert commands == {b"S00", b"S20", b"S14"}


@pytest.mark.asyncio
async def test_get_panel_info_cached_returns_without_io(
    connection, client: Client, alarm: Alarm
):
    # If panel_info is already known, get_panel_info returns it and performs no I/O
    alarm.panel_info = PanelInfo(model=PanelVersionUpdate.Model.D16X, version="8.7")

    info = await client.get_panel_info()
    assert info.model == PanelVersionUpdate.Model.D16X
    assert info.version == "8.7"
    # No writes should have occurred
    assert connection.write.call_count == 0


@pytest.mark.asyncio
async def test_get_panel_info_probes_when_missing(
    connection, client: Client, alarm: Alarm
):
    # With no cached info, get_panel_info should send S17 and return parsed info
    alarm.panel_info = None

    # Patch send_command_and_wait to send S17 then return a PanelVersionUpdate
    orig_send_command = client.send_command

    async def fake_scaw(command: str, timeout: float | None = 5.0):
        await orig_send_command(command)
        return panel_version_response(PanelVersionUpdate.Model.D32X, 8, 7)

    client.send_command_and_wait = fake_scaw  # type: ignore[assignment]

    info = await client.get_panel_info()
    # Ensure S17 was sent
    assert connection.write.call_count == 1
    first = get_data(connection.write.call_args_list[0][0][0])
    assert first == b"S17"
    # Info returned should match the fake response
    assert info.model == PanelVersionUpdate.Model.D32X
    assert info.version == "8.7"


@pytest.mark.asyncio
async def test_send_command(connection, client):
    await client.send_command("ABCDEFGHI")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"ABCDEFGHI"


@pytest.mark.asyncio
async def test_send_command_has_newlines(connection, client):
    await client.send_command("A1234E")
    assert connection.write.call_count == 1
    assert connection.write.call_args[0][0][-2:] == b"\r\n"


@pytest.mark.asyncio
async def test_send_command_2(connection, client):
    await client.send_command("FOOBARBAZ")
    assert connection.write.call_count == 1
    print(connection.write.call_args[0][0])
    assert get_data(connection.write.call_args[0][0]) == b"FOOBARBAZ"


def test_keepalive_bad_data_does_not_crash():
    # TODO(NW): Find a way to test this functionality inside the recv loop
    pass


def test_keepalive_unknown_event_does_not_crash():
    # TODO(NW): Find a way to test this functionality inside the recv loop
    pass


def test_keepalive_polls_alarm_connection():
    # TODO(NW): Find a way to test this functionality inside the send loop
    pass


def test_on_event_received_callback():
    # TODO(NW): Find a way to test this functionality inside the recv loop
    pass


def test_on_state_change_callback_is_registered(client, alarm):
    cb = Mock()
    client.on_state_change(cb)
    assert alarm.on_state_change.call_count == 1
    assert alarm.on_state_change.call_args[0][0] == cb


def test_on_zone_change_callback_is_registered(client, alarm):
    cb = Mock()
    client.on_zone_change(cb)
    assert alarm.on_zone_change.call_count == 1
    assert alarm.on_zone_change.call_args[0][0] == cb


@pytest.mark.asyncio
async def test_close(connection, client):
    await client.close()
    assert connection.close.call_count == 1


@pytest.mark.asyncio
async def test_send_command_and_wait_sends_payload(connection, client):
    # Start, allow send to occur
    task = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))
    await asyncio.sleep(0)
    # Verify write and payload
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"S14"
    # Complete the task by dispatching a matching response (no assertions here)
    pkt = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data="140000",
        timestamp=None,
        is_user_interface_resp=True,
    )
    client._dispatch_event(BaseEvent.decode(pkt), pkt)
    await task


@pytest.mark.asyncio
async def test_send_command_and_wait_resolves_on_response(connection, client):
    task = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))
    # Allow registration of the waiter
    await asyncio.sleep(0)
    # Simulate incoming USER_INTERFACE response for request id 14
    pkt = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data="140000",
        timestamp=None,
        is_user_interface_resp=True,
    )
    event = BaseEvent.decode(pkt)
    client._dispatch_event(event, pkt)
    result = await task
    assert isinstance(result, StatusUpdate)
    assert result.request_id == StatusUpdate.RequestID.ARMING


@pytest.mark.asyncio
async def test_send_command_and_wait_times_out(connection, client):
    with pytest.raises(asyncio.TimeoutError):
        await client.send_command_and_wait("S14", timeout=0.01)


@pytest.mark.asyncio
async def test_send_command_and_wait_raises_for_non_status(connection, client):
    with pytest.raises(ValueError):
        await client.send_command_and_wait("A1234E", timeout=0.01)


@pytest.mark.asyncio
async def test_multiple_waiters_resolve_together(connection, client):
    # Two concurrent S14 waits
    t1 = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))
    t2 = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))

    # Ensure two commands were sent
    await asyncio.sleep(0)
    assert connection.write.call_count == 2

    # Single response should resolve both waiters
    pkt = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data="140001",
        timestamp=None,
        is_user_interface_resp=True,
    )
    e = BaseEvent.decode(pkt)
    client._dispatch_event(e, pkt)

    r1 = await t1
    r2 = await t2
    assert isinstance(r1, StatusUpdate) and isinstance(r2, StatusUpdate)
    assert r1.request_id == StatusUpdate.RequestID.ARMING
    assert r2.request_id == StatusUpdate.RequestID.ARMING


@pytest.mark.asyncio
async def test_followup_response_for_same_id_is_handled(connection, client):
    # Two concurrent S14 waiters resolve together on first response
    t1 = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))
    t2 = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))
    await asyncio.sleep(0)
    assert connection.write.call_count == 2

    pkt1 = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data="140000",
        timestamp=None,
        is_user_interface_resp=True,
    )
    e1 = BaseEvent.decode(pkt1)
    client._dispatch_event(e1, pkt1)
    r1 = await t1
    r2 = await t2
    assert isinstance(r1, StatusUpdate) and isinstance(r2, StatusUpdate)

    # Start a new waiter after the first response; it should be resolved by a
    # follow-up response for the same request id.
    t3 = asyncio.create_task(client.send_command_and_wait("S14", timeout=1.0))
    await asyncio.sleep(0)
    assert connection.write.call_count == 3

    pkt2 = Packet(
        address=0x00,
        seq=0x00,
        command=CommandType.USER_INTERFACE,
        data="140001",
        timestamp=None,
        is_user_interface_resp=True,
    )
    e2 = BaseEvent.decode(pkt2)
    client._dispatch_event(e2, pkt2)
    r3 = await t3
    assert isinstance(r3, StatusUpdate)
    assert r3.request_id == StatusUpdate.RequestID.ARMING


@pytest.fixture
def alarm() -> Alarm:
    return Mock()


@pytest.fixture
def connection() -> Connection:
    return AsyncMock(Connection)


@pytest.fixture
def client(connection, alarm) -> Client:
    return Client(connection=connection, alarm=alarm)
