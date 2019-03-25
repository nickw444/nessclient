import asyncio
import datetime
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
    """
    :param update_interval: Frequency (in seconds) to trigger a full state
        refresh
    :param infer_arming_state: Infer the `DISARMED` arming state only via
        system status events. This works around a bug with some panels
        (`<v5.8`) which emit `update.status = []` when they are armed.
    """
    def __init__(self,
                 connection: Optional[Connection] = None,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None,
                 update_interval: int = 60,
                 infer_arming_state: bool = False,
                 alarm: Optional[Alarm] = None):
        if connection is None:
            assert host is not None
            assert port is not None
            assert loop is not None
            connection = IP232Connection(host=host, port=port, loop=loop)

        if alarm is None:
            alarm = Alarm(infer_arming_state=infer_arming_state)

        self.alarm = alarm
        self._on_event_received: Optional[Callable[[BaseEvent], None]] = None
        self._connection = connection
        self._closed = False
        self._backoff = Backoff()
        self._connect_lock = asyncio.Lock()
        self._last_recv: Optional[datetime.datetime] = None
        self._update_interval = update_interval

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
        _LOGGER.debug("Requesting state update from server (S00, S14)")
        await asyncio.gather(
            # List unsealed Zones
            self.send_command('S00'),
            # Arming status update
            self.send_command('S14'),
        )

    async def _connect(self) -> None:
        async with self._connect_lock:
            if self._should_reconnect():
                _LOGGER.debug('Closing stale connection and reconnecting')
                await self._connection.close()

            while not self._connection.connected:
                _LOGGER.debug('Attempting to connect')
                try:
                    await self._connection.connect()
                except (ConnectionRefusedError, OSError) as e:
                    _LOGGER.warning('Failed to connect: %s', e)
                    await sleep(self._backoff.duration())

                self._last_recv = datetime.datetime.now()

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
        payload = packet.encode() + '\r\n'
        _LOGGER.debug('Sending payload: %s', repr(payload))
        return await self._connection.write(payload.encode('ascii'))

    async def _recv_loop(self) -> None:
        while not self._closed:
            await self._connect()

            while True:
                data = await self._connection.read()
                if data is None:
                    _LOGGER.debug("Received None data from connection.read()")
                    break

                self._last_recv = datetime.datetime.now()
                try:
                    decoded_data = data.decode('utf-8').strip()
                except UnicodeDecodeError:
                    _LOGGER.warning("Failed to decode data", exc_info=True)
                    continue

                _LOGGER.debug("Decoding data: '%s'", decoded_data)
                if len(decoded_data) > 0:
                    try:
                        pkt = Packet.decode(decoded_data)
                        event = BaseEvent.decode(pkt)
                    except Exception:
                        _LOGGER.warning("Failed to decode packet", exc_info=True)
                        continue

                    if self._on_event_received is not None:
                        self._on_event_received(event)

                    self.alarm.handle_event(event)

    def _should_reconnect(self) -> bool:
        now = datetime.datetime.now()
        return self._last_recv is not None and self._last_recv < now - datetime.timedelta(
            seconds=self._update_interval + 30)

    async def _update_loop(self) -> None:
        """Schedule a state update to keep the connection alive"""
        await asyncio.sleep(self._update_interval)
        while not self._closed:
            await self.update()
            await asyncio.sleep(self._update_interval)

    async def keepalive(self) -> None:
        await asyncio.gather(
            self._recv_loop(),
            self._update_loop(),
        )

    async def close(self) -> None:
        self._closed = True
        await self._connection.close()

    def on_state_change(self, f: Callable[[ArmingState], None]
                        ) -> Callable[[ArmingState], None]:
        self.alarm.on_state_change(f)
        return f

    def on_zone_change(self, f: Callable[[int, bool], None]
                       ) -> Callable[[int, bool], None]:
        self.alarm.on_zone_change(f)
        return f

    def on_event_received(self, f: Callable[[BaseEvent], None]
                          ) -> Callable[[BaseEvent], None]:
        self._on_event_received = f
        return f
