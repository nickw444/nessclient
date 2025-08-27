import asyncio
import datetime
import logging
from asyncio import sleep
from typing import Callable, Dict

from justbackoff import Backoff

from .alarm import ArmingState, Alarm, ArmingMode, PanelInfo
from .connection import Connection, IP232Connection, Serial232Connection
from .event import BaseEvent, DecodeOptions, StatusUpdate, PanelVersionUpdate
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

    def __init__(
        self,
        connection: Connection | None = None,
        host: str | None = None,
        port: int | None = None,
        serial_tty: str | None = None,
        update_interval: int = 60,
        infer_arming_state: bool = False,
        alarm: Alarm | None = None,
        decode_options: DecodeOptions | None = None,
    ):
        if connection is None:
            if host is not None and port is not None:
                connection = IP232Connection(host=host, port=port)
            elif serial_tty is not None:
                connection = Serial232Connection(tty_path=serial_tty)
            else:
                raise ValueError(
                    "Must provide host+port or serial_tty or connection object"
                )

        if alarm is None:
            alarm = Alarm(infer_arming_state=infer_arming_state)

        self.alarm = alarm
        self._decode_options = decode_options
        self._on_event_received: Callable[[BaseEvent], None] | None = None
        self._connection = connection
        self._closed = False
        self._backoff = Backoff()
        self._connect_lock = asyncio.Lock()
        self._last_recv: datetime.datetime | None = None
        self._update_interval = update_interval
        # Track pending USER_INTERFACE status request futures keyed by request id
        # Only a single Future is retained per request id; concurrent waiters share it.
        self._pending_ui_requests: Dict[int, asyncio.Future[StatusUpdate]] = {}
        self._pending_ui_lock = asyncio.Lock()

    async def arm_away(self, code: str | None = None) -> None:
        command = "A{}E".format(code if code else "")
        return await self.send_command(command)

    async def arm_home(self, code: str | None = None) -> None:
        command = "H{}E".format(code if code else "")
        return await self.send_command(command)

    async def disarm(self, code: str) -> None:
        command = "{}E".format(code)
        return await self.send_command(command)

    async def panic(self, code: str) -> None:
        command = "*{}#".format(code)
        return await self.send_command(command)

    async def aux(self, output_id: int, state: bool = True) -> None:
        command = "{}{}{}".format(output_id, output_id, "*" if state else "#")
        return await self.send_command(command)

    async def get_panel_info(self) -> PanelInfo:
        """Fetch and return panel information (model and version)."""
        # Return panel info if we already know it.
        if self.alarm.panel_info is not None:
            return self.alarm.panel_info

        resp = await self.send_command_and_wait("S17")
        if isinstance(resp, PanelVersionUpdate):
            # The event dispatcher will also dispatch the event to the alarm
            # entity which will handle the PanelVersionUpdate internally to set
            # the panel_info property.
            return PanelInfo(model=resp.model, version=resp.version)

        raise RuntimeError(f"Unexpected response to S17: {resp}")

    async def update(self) -> None:
        """Force update of alarm status and zones"""
        _LOGGER.debug("Requesting state update from server (S00, S20, S14)")
        await asyncio.gather(
            # List unsealed Zones 1-16
            self.send_command("S00"),
            # List unsealed Zones 17-32
            # Note: Request this for all panels. Many panels can exceed 16 zones
            # via expansion modules, but the ASCII protocol does not provide a
            # reliable way to detect expansion presence. Panels tested tolerate
            # S20 when only 8/16 zones are configured and simply return an empty
            # set for zones 17–32. The extra status request is negligible
            # overhead and guarantees we observe zones 17–32 whenever they exist.
            self.send_command("S20"),
            # Arming status update
            self.send_command("S14"),
        )

    async def _connect(self) -> None:
        async with self._connect_lock:
            if self._should_reconnect():
                _LOGGER.debug("Closing stale connection and reconnecting")
                await self._connection.close()

            while not self._connection.connected:
                _LOGGER.debug("Attempting to connect")
                try:
                    await self._connection.connect()
                except (ConnectionRefusedError, OSError) as e:
                    _LOGGER.warning("Failed to connect: %s", e)
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
        payload = packet.encode() + "\r\n"
        _LOGGER.debug("Sending payload: %s", repr(payload))
        return await self._connection.write(payload.encode("ascii"))

    async def send_command_and_wait(
        self, command: str, timeout: float | None = 5.0
    ) -> StatusUpdate:
        """Send a command and await a matching USER_INTERFACE response.

        - Requires the command to be a status request (SXX). If not, raises a
          ValueError because those commands do not elicit a status response.
        - Resolves when a matching USER_INTERFACE response arrives, else times out.
        """
        waiter_req_id: int | None = None
        try:
            if len(command) >= 3 and command[0].upper() == "S":
                waiter_req_id = int(command[1:3], 16)
        except Exception:
            waiter_req_id = None

        if waiter_req_id is None:
            raise ValueError(f"Command does not expect a status response: '{command}'")

        loop = asyncio.get_running_loop()
        async with self._pending_ui_lock:
            existing = self._pending_ui_requests.get(waiter_req_id)
            if existing is None or existing.done():
                fut: asyncio.Future[StatusUpdate] = loop.create_future()
                self._pending_ui_requests[waiter_req_id] = fut
            else:
                fut = existing

        try:
            await self.send_command(command)
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            # Do not clear mapping here; dispatcher pops the future on resolution.
            pass

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
                    decoded_data = data.decode("utf-8").strip()
                except UnicodeDecodeError:
                    _LOGGER.warning("Failed to decode data", exc_info=True)
                    continue

                _LOGGER.debug("Decoding data: '%s'", decoded_data)
                if len(decoded_data) > 0:
                    try:
                        pkt = Packet.decode(decoded_data)
                        event = BaseEvent.decode(pkt, self._decode_options)
                    except Exception:
                        _LOGGER.warning("Failed to decode packet", exc_info=True)
                        continue

                    self._dispatch_event(event, pkt)

    def _should_reconnect(self) -> bool:
        now = datetime.datetime.now()
        return self._last_recv is not None and self._last_recv < now - datetime.timedelta(
            seconds=self._update_interval + 30
        )

    def _dispatch_event(self, event: BaseEvent, pkt: Packet) -> None:
        """Internal dispatcher for decoded events.

        - Completes any pending USER_INTERFACE status request futures.
        - Invokes the user callback and updates the Alarm.
        """
        # Resolve pending status requests if applicable
        if isinstance(event, StatusUpdate):
            req_id = int(event.request_id.value)
            ev: StatusUpdate = event

            if self._pending_ui_requests.get(req_id):

                async def _resolve() -> None:
                    fut: asyncio.Future[StatusUpdate] | None = None
                    async with self._pending_ui_lock:
                        fut = self._pending_ui_requests.pop(req_id, None)
                    if fut is not None and not fut.done():
                        try:
                            fut.set_result(ev)
                        except Exception:
                            pass

                asyncio.create_task(_resolve())

        if self._on_event_received is not None:
            try:
                self._on_event_received(event)
            except Exception:
                _LOGGER.warning("on_event_received callback raised", exc_info=True)

        self.alarm.handle_event(event)

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

    def on_state_change(
        self, f: Callable[[ArmingState, ArmingMode | None], None]
    ) -> Callable[[ArmingState, ArmingMode | None], None]:
        self.alarm.on_state_change(f)
        return f

    def on_zone_change(
        self, f: Callable[[int, bool], None]
    ) -> Callable[[int, bool], None]:
        self.alarm.on_zone_change(f)
        return f

    def on_event_received(
        self, f: Callable[[BaseEvent], None]
    ) -> Callable[[BaseEvent], None]:
        self._on_event_received = f
        return f
