import asyncio

import pytest
from unittest.mock import AsyncMock, Mock, call

from nessclient.alarm import Alarm, ArmingMode, ArmingState
from nessclient.client import Client
from nessclient.connection import Connection
from nessclient.event import (
    PanelVersionUpdate,
    StatusUpdate,
    SystemStatusEvent,
)


@pytest.mark.asyncio
async def test_ascii_payload_updates_alarm_state(
    client: Client, connection: Connection, alarm: Alarm
) -> None:
    # Example taken from protocol specification: Duress event
    ascii_payload = "870203610201840612010743008D"
    await _feed_ascii(client, connection, ascii_payload)
    assert alarm.arming_state == ArmingState.TRIGGERED


@pytest.mark.asyncio
async def test_zone_events_update_zone_state(
    client: Client, connection: Connection, alarm: Alarm
) -> None:
    # Zone 3 unsealed at 23:45 on 10/5/2008
    await _feed_ascii(client, connection, "87020361000301080510234500E5")
    assert alarm.zones[2].triggered is True

    # Zone 3 sealed one minute later
    await _feed_ascii(client, connection, "87020361010301080510234600E3")
    assert alarm.zones[2].triggered is False


@pytest.mark.asyncio
async def test_arming_events_update_alarm_state(
    client: Client, connection: Connection, alarm: Alarm
) -> None:
    # User 1 initiated arming away at 23:45 on 10/5/2008
    await _feed_ascii(client, connection, "87020361240101080510234500E1")
    assert alarm.arming_state == ArmingState.ARMING

    # User 1 disarmed at 23:46 on 10/5/2008
    await _feed_ascii(client, connection, "870203612F0101080510234600CE")
    assert alarm.arming_state == ArmingState.DISARMED


@pytest.mark.asyncio
async def test_arm_away_emits_ascii_payload(
    client: Client, connection: Connection
) -> None:
    await client.arm_away("1234")
    connection.write.assert_called_once_with(b"8300660A1234E49\r\n")


@pytest.mark.asyncio
async def test_arm_home_emits_ascii_payload(
    client: Client, connection: Connection
) -> None:
    await client.arm_home("1234")
    connection.write.assert_called_once_with(b"8300660H1234E42\r\n")


@pytest.mark.asyncio
async def test_disarm_emits_ascii_payload(client: Client, connection: Connection) -> None:
    await client.disarm("1234")
    connection.write.assert_called_once_with(b"83005601234E8B\r\n")


@pytest.mark.asyncio
async def test_panic_emits_ascii_payload(client: Client, connection: Connection) -> None:
    await client.panic("1234")
    connection.write.assert_called_once_with(b"8300660*1234#82\r\n")


@pytest.mark.asyncio
async def test_aux_on_emits_ascii_payload(client: Client, connection: Connection) -> None:
    await client.aux(3, True)
    connection.write.assert_called_once_with(b"830036033*0C\r\n")


@pytest.mark.asyncio
async def test_aux_off_emits_ascii_payload(
    client: Client, connection: Connection
) -> None:
    await client.aux(3, False)
    connection.write.assert_called_once_with(b"830036033#13\r\n")


@pytest.mark.asyncio
async def test_update_emits_ascii_payloads(
    client: Client, connection: Connection
) -> None:
    await client.update()
    connection.write.assert_any_call(b"8300360S00E9\r\n")
    connection.write.assert_any_call(b"8300360S20E7\r\n")
    connection.write.assert_any_call(b"8300360S14E4\r\n")
    assert connection.write.await_count == 3


@pytest.mark.asyncio
async def test_send_command_emits_ascii_payload(
    client: Client,
    connection: Connection,
) -> None:
    await client.send_command("S30")
    connection.write.assert_called_once_with(b"8300360S30E6\r\n")


@pytest.mark.asyncio
async def test_send_command_and_wait_returns_status_update(
    client: Client,
    connection: Connection,
) -> None:
    ascii_payload = "8200036014000048"
    _prepare_ascii(client, connection, ascii_payload)

    task = asyncio.create_task(client.send_command_and_wait("S14"))
    await asyncio.sleep(0)
    await client._recv_loop()
    resp = await task

    connection.write.assert_called_once_with(b"8300360S14E4\r\n")
    assert isinstance(resp, StatusUpdate)
    assert resp.request_id == StatusUpdate.RequestID.ARMING


@pytest.mark.asyncio
async def test_get_panel_info_emits_ascii_payload(
    client: Client,
    connection: Connection,
    alarm: Alarm,
) -> None:
    ascii_payload = "8200036017008736"
    _prepare_ascii(client, connection, ascii_payload)

    task = asyncio.create_task(client.get_panel_info())
    await asyncio.sleep(0)
    await client._recv_loop()
    info = await task

    connection.write.assert_called_once_with(b"8300360S17E1\r\n")
    assert info.version == "8.7"
    assert info.model == PanelVersionUpdate.Model.D16X
    assert alarm.panel_info == info


@pytest.mark.asyncio
async def test_state_change_callback_invoked(
    client: Client, connection: Connection, alarm: Alarm
) -> None:
    callback = Mock()
    client.on_state_change(callback)

    await _feed_ascii(client, connection, "87020361240101080510234500E1")
    await _feed_ascii(client, connection, "870203612F0101080510234600CE")

    assert callback.call_count == 2
    assert callback.call_args_list == [
        call(ArmingState.ARMING, ArmingMode.ARMED_AWAY),
        call(ArmingState.DISARMED, None),
    ]


@pytest.mark.asyncio
async def test_zone_change_callback_invoked(
    client: Client, connection: Connection, alarm: Alarm
) -> None:
    callback = Mock()
    client.on_zone_change(callback)

    await _feed_ascii(client, connection, "87020361000301080510234500E5")
    await _feed_ascii(client, connection, "87020361010301080510234600E3")

    assert callback.call_count == 2
    assert callback.call_args_list == [call(3, True), call(3, False)]


@pytest.mark.asyncio
async def test_event_received_callback_invoked(
    client: Client, connection: Connection, alarm: Alarm
) -> None:
    callback = Mock()
    client.on_event_received(callback)

    await _feed_ascii(client, connection, "87020361000301080510234500E5")

    assert callback.call_count == 1
    event = callback.call_args[0][0]
    assert isinstance(event, SystemStatusEvent)
    assert event.type == SystemStatusEvent.EventType.UNSEALED
    assert event.zone == 3


@pytest.fixture
def alarm() -> Alarm:
    return Alarm()


@pytest.fixture
def connection() -> Connection:
    return AsyncMock(Connection)


@pytest.fixture
def client(connection: Connection, alarm: Alarm) -> Client:
    return Client(connection=connection, alarm=alarm)


def _prepare_ascii(client: Client, connection: Connection, ascii_payload: str) -> None:
    connection.connected = False

    async def connect() -> bool:
        connection.connected = True
        return True

    connection.connect.side_effect = connect

    payload_iter = iter([ascii_payload.encode("ascii"), None])

    async def read() -> bytes | None:
        data = next(payload_iter)
        if data is None:
            client._closed = True
        return data

    connection.read.side_effect = read
    client._closed = False


async def _feed_ascii(client: Client, connection: Connection, ascii_payload: str) -> None:
    _prepare_ascii(client, connection, ascii_payload)
    await client._recv_loop()
