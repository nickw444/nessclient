"""Test the API of the nessclient Client class."""

from unittest.mock import Mock, AsyncMock

import pytest

from nessclient import Client
from nessclient.alarm import Alarm
from nessclient.connection import Connection


def get_data(pkt: bytes) -> bytes:
    """Get the data part from a UI request packet."""
    return pkt[7:-4]


@pytest.mark.asyncio
async def test_arm_away(connection: AsyncMock, client: Client) -> None:
    """Test that the arm_away() method sends the correct packet data."""
    await client.arm_away("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"A1234E"


@pytest.mark.asyncio
async def test_arm_home(connection: AsyncMock, client: Client) -> None:
    """Test that the arm_home() method sends the correct packet data."""
    await client.arm_home("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"H1234E"


@pytest.mark.asyncio
async def test_disarm(connection: AsyncMock, client: Client) -> None:
    """Test that the disarm() method sends the correct packet data."""
    await client.disarm("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"1234E"


@pytest.mark.asyncio
async def test_panic(connection: AsyncMock, client: Client) -> None:
    """Test that the panic() method sends the correct packet data."""
    await client.panic("1234")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"*1234#"


@pytest.mark.asyncio
async def test_aux_on(connection: AsyncMock, client: Client) -> None:
    """Test that the aux() method (turn on) sends the correct packet data."""
    await client.aux(1, True)
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"11*"


@pytest.mark.asyncio
async def test_aux_off(connection: AsyncMock, client: Client) -> None:
    """Test that the aux() method (turn off) sends the correct packet data."""
    await client.aux(1, False)
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"11#"


@pytest.mark.asyncio
async def test_update(connection: AsyncMock, client: Client) -> None:
    """Test that the update() method sends the correct Status Request packet data."""
    await client.update()
    assert connection.write.call_count == 2
    commands = {
        get_data(connection.write.call_args_list[0][0][0]),
        get_data(connection.write.call_args_list[1][0][0]),
    }
    assert commands == {b"S00", b"S14"}


@pytest.mark.asyncio
async def test_send_command(connection: AsyncMock, client: Client) -> None:
    """Test that the send_command sends the requested packet data."""
    await client.send_command("ABCDEFGHI")
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b"ABCDEFGHI"


@pytest.mark.asyncio
async def test_send_command_has_newlines(connection: AsyncMock, client: Client) -> None:
    """Test that the send_command sends packet with CRLF ending."""
    await client.send_command("A1234E")
    assert connection.write.call_count == 1
    assert connection.write.call_args[0][0][-2:] == b"\r\n"


@pytest.mark.asyncio
async def test_send_command_2(connection: AsyncMock, client: Client) -> None:
    """Test that the send_command sends the requested packet data (with '*', '#')."""
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


def test_on_state_change_callback_is_registered(client: Client, alarm: Mock) -> None:
    """Check on_state_change() callback gets provided to the alarm class."""
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
async def test_close(connection: AsyncMock, client: Client) -> None:
    """Check close() method calls the connection close method."""
    await client.close()
    assert connection.close.call_count == 1


@pytest.fixture
def alarm() -> Mock:
    """Mock alarm object fixture within the Client fixture."""
    return Mock()


@pytest.fixture
def connection() -> AsyncMock:
    """Mock connection object fixture within the Client fixture."""
    return AsyncMock(Connection)


@pytest.fixture
def client(connection: AsyncMock, alarm: Alarm) -> Client:
    """Client object fixture for tests."""
    return Client(connection=connection, alarm=alarm)
