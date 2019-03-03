import pytest
from asynctest import MagicMock

from nessclient import Client
from nessclient.connection import Connection


def get_data(pkt: bytes) -> bytes:
    return pkt[7:-4]


@pytest.mark.asyncio
async def test_arm_away(connection, client):
    await client.arm_away('1234')
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'A1234E'


@pytest.mark.asyncio
async def test_arm_home(connection, client):
    await client.arm_home('1234')
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'H1234E'


@pytest.mark.asyncio
async def test_disarm(connection, client):
    await client.disarm('1234')
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'1234E'


@pytest.mark.asyncio
async def test_panic(connection, client):
    await client.panic('1234')
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'*1234#'


@pytest.mark.asyncio
async def test_aux_on(connection, client):
    await client.aux(1, True)
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'11*'


@pytest.mark.asyncio
async def test_aux_off(connection, client):
    await client.aux(1, False)
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'11#'


@pytest.mark.asyncio
async def test_update(connection, client):
    await client.update()
    assert connection.write.call_count == 2
    assert get_data(connection.write.call_args_list[0][0][0]) == b'S00'
    assert get_data(connection.write.call_args_list[1][0][0]) == b'S14'


@pytest.mark.asyncio
async def test_send_command(connection, client):
    await client.send_command('ABCDEFGHI')
    assert connection.write.call_count == 1
    assert get_data(connection.write.call_args[0][0]) == b'ABCDEFGHI'


@pytest.mark.asyncio
async def test_send_command_2(connection, client):
    await client.send_command('FOOBARBAZ')
    assert connection.write.call_count == 1
    print(connection.write.call_args[0][0])
    assert get_data(connection.write.call_args[0][0]) == b'FOOBARBAZ'


@pytest.mark.asyncio
async def test_close(connection, client):
    await client.close()
    assert connection.close.call_count == 1


@pytest.fixture
def connection():
    return MagicMock(Connection)


@pytest.fixture
def client(connection):
    return Client(connection=connection)
