import asyncio
import logging
from asyncio import sleep
from typing import Optional, Callable

from justbackoff import Backoff

from .alarm import ArmingState, Alarm
from .connection import Connection, IP232Connection
from .event import BaseEvent
from .packet import CommandType, Packet

_LOGGER = logging.getLogger(__name__)


class Client:
    def __init__(self,
                 connection: Optional[Connection] = None,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
        if connection is None:
            assert host is not None
            assert port is not None
            assert loop is not None
            connection = IP232Connection(host=host, port=port, loop=loop)

        self.alarm = Alarm()
        self._on_event_received: Optional[Callable[[BaseEvent], None]] = None
        self._connection = connection
        self._closed = False
        self._backoff = Backoff()

    async def arm_away(self, code: Optional[str] = None) -> None:
        command = 'A{}E'.format(code if code else '')
        return await self.send_command(command)

    async def arm_home(self, code: Optional[str] = None) -> None:
        command = 'H{}E'.format(code if code else '')
        return await self.send_command(command)

    async def disarm(self, code: str) -> None:
        command = '{}E'.format(code)
        return await self.send_command(command)

    async def panic(self, code: str) -> None:
        command = '*{}#'.format(code)
        return await self.send_command(command)

    async def aux(self, output_id: int, state: bool = True) -> None:
        command = '{}{}{}'.format(
            output_id, output_id,
            '*' if state else '#')
        return await self.send_command(command)

    async def update(self) -> None:
        """Force update of alarm status and zones"""
        await asyncio.gather(
            # List unsealed Zones
            self.send_command('S00'),
            # Arming status update
            self.send_command('S14'),
        )

    async def _connect(self) -> None:
        while not self._connection.connected:
            try:
                await self._connection.connect()
            except (ConnectionRefusedError, OSError) as e:
                _LOGGER.warning('Failed to connect: %s', e)
                await sleep(self._backoff.duration())

        self._backoff.reset()

    async def send_command(self, command: str) -> None:
        packet = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data=command,
            timestamp=None,
        )
        await self._connect()
        return await self._connection.write(packet.encode().encode('ascii'))

    async def keepalive(self) -> None:
        while not self._closed:
            await self._connect()

            while True:
                data = await self._connection.read()
                if data is None:
                    break

                decoded_data = data.decode('utf-8').strip()
                _LOGGER.debug("Decoding data: '%s'", decoded_data)
                if len(decoded_data) > 0:
                    pkt = Packet.decode(decoded_data)
                    event = BaseEvent.decode(pkt)
                    if self._on_event_received is not None:
                        self._on_event_received(event)

                    self.alarm.handle_event(event)

    def close(self) -> None:
        self._closed = True
        self._connection.close()

    def on_state_change(self, f: Callable[[ArmingState], None]
                        ) -> Callable[[ArmingState], None]:
        self.alarm._on_state_change = f
        return f

    def on_zone_change(self, f: Callable[[int, bool], None]
                       ) -> Callable[[int, bool], None]:
        self.alarm._on_zone_change = f
        return f

    def on_event_received(self, f: Callable[[BaseEvent], None]
                          ) -> Callable[[BaseEvent], None]:
        self._on_event_received = f
        return f
