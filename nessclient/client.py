import asyncio
import logging
import re
import time
import warnings
from typing import AsyncIterator, Callable, Dict, List

from justbackoff import Backoff
from serialx import SerialException

from .alarm import ArmingState, Alarm, ArmingMode, PanelInfo
from .connection import Connection, IP232Connection, Serial232Connection
from .errors import ClientClosedError, PanelNotRespondingError
from .event import BaseEvent, DecodeOptions, StatusUpdate, PanelVersionUpdate
from .packet import CommandType, Packet

_LOGGER = logging.getLogger(__name__)

# Transport errors that the reconnect loop retries
CONNECTION_ERRORS = (OSError, SerialException)

DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_RESPONSE_TIMEOUT = 10.0
DEFAULT_PROBE_TIMEOUT = 15.0

# Arming status: a read-only request answered by every supported panel
HEALTH_CHECK_COMMAND = "S14"

# Wait between refreshes while the panel is not answering
UNAVAILABLE_REFRESH_INTERVAL = 10.0

# Reopen a connection that has received nothing for this long beyond the
# refresh interval. Covers half-open TCP sessions and stalled proxies.
STALE_CONNECTION_GRACE = 30.0

_STATUS_REQUEST_RE = re.compile(r"^S[0-9A-F]{2}$", re.IGNORECASE)


def _redact_command(command: str) -> str:
    """Hide user codes, which are part of most non-status commands."""
    if _STATUS_REQUEST_RE.match(command):
        return command
    return re.sub(r"[0-9]", "*", command)


class Client:
    """
    :param update_interval: Frequency (in seconds) to trigger a full state
        refresh
    :param infer_arming_state: Infer the `DISARMED` arming state only via
        system status events. This works around a bug with some panels
        (`<v5.8`) which emit `update.status = []` when they are armed.
    :param connect_timeout: Deadline (in seconds) for a single attempt to open
        the connection.
    :param response_timeout: Deadline (in seconds) for the panel to answer the
        status request used to confirm that it is communicating.
    """

    def __init__(
        self,
        connection: Connection | None = None,
        host: str | None = None,
        port: int | None = None,
        serial_tty: str | None = None,
        update_interval: float = 60,
        infer_arming_state: bool = False,
        alarm: Alarm | None = None,
        decode_options: DecodeOptions | None = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        response_timeout: float = DEFAULT_RESPONSE_TIMEOUT,
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
        self._on_availability_change: Callable[[bool], None] | None = None
        self._event_subscribers: List[asyncio.Queue[BaseEvent]] = []
        self._connection = connection
        self._connect_timeout = connect_timeout
        self._response_timeout = response_timeout
        self._closed = False
        self._available = False
        self._backoff = Backoff()
        self._connect_failures = 0
        self._connect_lock = asyncio.Lock()
        # Pulsed whenever a session is established or the client is closed
        self._connection_event = asyncio.Event()
        # Set when state should be refreshed without waiting for the interval
        self._refresh_event = asyncio.Event()
        self._last_recv: float | None = None
        self._update_interval = update_interval
        self._recv_task: asyncio.Task[None] | None = None
        self._update_task: asyncio.Task[None] | None = None
        # Waiters for USER_INTERFACE status responses, keyed by request id. A
        # response resolves every waiter for its id; the panel answers repeated
        # requests for the same id identically, so they cannot be told apart.
        self._pending_ui_requests: Dict[int, List[asyncio.Future[StatusUpdate]]] = {}

    @property
    def available(self) -> bool:
        """Whether the panel answered the most recent status request."""
        return self._available

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
        warnings.warn(
            "Client.aux is deprecated; use aux_output instead",
            DeprecationWarning,
            stacklevel=2,
        )
        await self.aux_output(output_id, state)

    async def aux_output(self, output_id: int, state: bool = True) -> None:
        command = f"{output_id}{output_id}{'*' if state else '#'}"
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
        _LOGGER.debug("Requesting state update from server (S00, S20, S14, S18)")
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
            # Auxiliary outputs status
            self.send_command("S18"),
        )

    async def probe(self, timeout: float = DEFAULT_PROBE_TIMEOUT) -> StatusUpdate:
        """Confirm that the alarm panel is answering on this client's connection.

        Opens the connection if needed (a single attempt, without retrying),
        starts processing incoming data, and requests the arming status. The
        connection and receive processing stay active afterwards, call
        `keepalive()` to keep them running or `close()` to release them.

        :raises PanelNotRespondingError: the connection opened, but no valid
            matching response arrived before the deadline.
        :raises OSError: the connection could not be opened or was lost.
        :raises serialx.SerialException: the serial backend rejected the port.
        """
        connected = False
        try:
            async with asyncio.timeout(timeout):
                if self._receiving:
                    # The receive loop owns reconnection, never open a second
                    # connection alongside it.
                    if not self._connection.connected:
                        raise ConnectionError("Not connected to the alarm panel")
                else:
                    await self._connect_once()
                    self._start_receiving()
                connected = True
                response = await self.send_command_and_wait(
                    HEALTH_CHECK_COMMAND, timeout=None
                )
        except TimeoutError as err:
            if not connected:
                raise
            raise PanelNotRespondingError(
                "The alarm panel did not respond to a status request"
            ) from err

        self._set_available(True)
        return response

    @property
    def _receiving(self) -> bool:
        return self._recv_task is not None and not self._recv_task.done()

    def _start_receiving(self) -> asyncio.Task[None]:
        if self._recv_task is None or self._recv_task.done():
            self._recv_task = asyncio.create_task(
                self._recv_loop(), name="nessclient receive loop"
            )
        return self._recv_task

    async def _open_connection(self) -> None:
        """Make one attempt to open the connection."""
        await asyncio.wait_for(self._connection.connect(), self._connect_timeout)
        if self._closed:
            # Opened while shutting down, release it straight away
            await self._connection.close()
            raise ClientClosedError("Client is closed")

        if self._connect_failures:
            _LOGGER.info("Reconnected to the alarm panel")
        self._connect_failures = 0
        self._backoff.reset()
        self._last_recv = time.monotonic()
        self._refresh_event.set()
        self._pulse_connection_event()

    async def _connect_once(self) -> None:
        async with self._connect_lock:
            if self._closed:
                raise ClientClosedError("Client is closed")
            if not self._connection.connected:
                await self._open_connection()

    async def _connect(self) -> None:
        """Connect, retrying with bounded backoff until connected or closed."""
        while True:
            async with self._connect_lock:
                if self._closed:
                    raise ClientClosedError("Client is closed")
                if self._connection.connected:
                    return
                try:
                    await self._open_connection()
                    return
                except ClientClosedError:
                    raise
                except CONNECTION_ERRORS as e:
                    error = e

            self._connect_failures += 1
            delay = self._backoff.duration()
            _LOGGER.log(
                logging.INFO if self._connect_failures == 1 else logging.DEBUG,
                "Failed to connect to the alarm panel (%s), retrying in %.1fs",
                str(error) or type(error).__name__,
                delay,
            )
            await self._wait_for_connection_event(delay)

    async def _wait_for_connection_event(self, delay: float) -> None:
        """Sleep for `delay` seconds, waking early on connect or close."""
        if self._closed:
            return
        self._connection_event.clear()
        try:
            async with asyncio.timeout(delay):
                await self._connection_event.wait()
        except TimeoutError:
            pass

    async def _ensure_connected(self) -> None:
        if not self._receiving:
            await self._connect()
            return

        # The receive loop owns reconnection, wait for it to succeed
        while not self._connection.connected:
            if self._closed:
                raise ClientClosedError("Client is closed")
            if not self._receiving:
                await self._connect()
                return
            self._connection_event.clear()
            await self._connection_event.wait()

    def _pulse_connection_event(self) -> None:
        self._connection_event.set()

    async def send_command(self, command: str) -> None:
        packet = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data=command,
            timestamp=None,
        )
        await self._ensure_connected()
        payload = packet.encode() + "\r\n"
        _LOGGER.debug("Sending command: %s", _redact_command(command))
        return await self._connection.write(payload.encode("ascii"))

    async def send_command_and_wait(
        self, command: str, timeout: float | None = 5.0
    ) -> StatusUpdate:
        """Send a command and await a matching USER_INTERFACE response.

        - Requires the command to be a status request (SXX). If not, raises a
          ValueError because those commands do not elicit a status response.
        - Requires incoming data to be processed, by `keepalive()` or `probe()`.
        - Resolves when a matching USER_INTERFACE response arrives, else times out.
        - Raises ConnectionError if the connection is lost while waiting, so a
          response from a later session is never matched to this request.
        """
        waiter_req_id: int | None = None
        try:
            if len(command) >= 3 and command[0].upper() == "S":
                waiter_req_id = int(command[1:3], 16)
        except Exception:
            waiter_req_id = None

        if waiter_req_id is None:
            raise ValueError(f"Command does not expect a status response: '{command}'")

        fut: asyncio.Future[StatusUpdate] = asyncio.get_running_loop().create_future()
        self._pending_ui_requests.setdefault(waiter_req_id, []).append(fut)
        try:
            await self.send_command(command)
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            waiters = self._pending_ui_requests.get(waiter_req_id)
            if waiters is not None and fut in waiters:
                waiters.remove(fut)
                if not waiters:
                    del self._pending_ui_requests[waiter_req_id]
            if fut.done() and not fut.cancelled():
                # Mark a failure delivered before we started waiting as retrieved
                fut.exception()

    def _fail_pending_requests(self, error: Exception) -> None:
        pending, self._pending_ui_requests = self._pending_ui_requests, {}
        for waiters in pending.values():
            for fut in waiters:
                if not fut.done():
                    fut.set_exception(error)

    async def _recv_loop(self) -> None:
        try:
            while not self._closed:
                try:
                    await self._connect()
                except ClientClosedError:
                    return

                while True:
                    data = await self._connection.read()
                    if data is None:
                        _LOGGER.debug("Received None data from connection.read()")
                        break

                    self._last_recv = time.monotonic()
                    self._handle_data(data)

                self._fail_pending_requests(
                    ConnectionError("Connection to the alarm panel was lost")
                )
                if not self._closed:
                    self._set_available(False)
        finally:
            # Wake commands waiting on this loop so they can observe its exit
            self._pulse_connection_event()

    def _handle_data(self, data: bytes) -> None:
        try:
            decoded_data = data.decode("utf-8").strip()
        except UnicodeDecodeError:
            _LOGGER.warning("Failed to decode data", exc_info=True)
            return

        _LOGGER.debug("Decoding data: '%s'", decoded_data)
        if len(decoded_data) > 0:
            try:
                pkt = Packet.decode(decoded_data)
                event = BaseEvent.decode(pkt, self._decode_options)
            except Exception:
                _LOGGER.warning("Failed to decode packet", exc_info=True)
                return

            self._dispatch_event(event, pkt)

    def _dispatch_event(self, event: BaseEvent, pkt: Packet) -> None:
        """Internal dispatcher for decoded events.

        - Completes any pending USER_INTERFACE status request futures.
        - Invokes the user callback and updates the Alarm.
        """
        # Resolve pending status requests if applicable
        if isinstance(event, StatusUpdate):
            req_id = int(event.request_id.value)
            for fut in self._pending_ui_requests.pop(req_id, []):
                if not fut.done():
                    fut.set_result(event)

        if self._on_event_received is not None:
            try:
                self._on_event_received(event)
            except Exception:
                _LOGGER.warning("on_event_received callback raised", exc_info=True)

        for q in list(self._event_subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass

        self.alarm.handle_event(event)

    def _set_available(self, available: bool) -> None:
        if available == self._available:
            return

        self._available = available
        _LOGGER.info(
            "Communication with the alarm panel %s",
            "established" if available else "lost",
        )
        if self._on_availability_change is not None:
            try:
                self._on_availability_change(available)
            except Exception:
                _LOGGER.warning("on_availability_change callback raised", exc_info=True)

    def _is_stale(self) -> bool:
        return (
            self._last_recv is not None
            and time.monotonic() - self._last_recv
            > self._update_interval + STALE_CONNECTION_GRACE
        )

    async def _refresh(self) -> None:
        """Request current state and confirm that the panel answers."""
        try:
            for command in ("S00", "S20", "S18"):
                # A serial panel may drop a burst of back-to-back requests.
                try:
                    await self.send_command_and_wait(
                        command, timeout=self._response_timeout
                    )
                except TimeoutError:
                    # Older panels may not implement every status report.
                    # The arming status below determines availability.
                    _LOGGER.debug("No response to %s", command)
            await self.send_command_and_wait(
                HEALTH_CHECK_COMMAND, timeout=self._response_timeout
            )
        except TimeoutError:
            if self._closed:
                return
            _LOGGER.debug("No response to %s", HEALTH_CHECK_COMMAND)
            self._set_available(False)
            if self._is_stale():
                _LOGGER.debug("Nothing received recently, reopening the connection")
                await self._connection.close()
            return
        except CONNECTION_ERRORS as e:
            # The receive loop reports and recovers from lost connections
            _LOGGER.debug("State refresh failed: %s", e)
            return

        self._set_available(True)

    async def _update_loop(self) -> None:
        """Refresh state periodically and after each new connection."""
        while not self._closed:
            interval = (
                self._update_interval
                if self._available
                else min(self._update_interval, UNAVAILABLE_REFRESH_INTERVAL)
            )
            try:
                async with asyncio.timeout(interval):
                    await self._refresh_event.wait()
            except TimeoutError:
                pass

            self._refresh_event.clear()
            if self._closed:
                return
            if self._connection.connected:
                await self._refresh()

    async def keepalive(self) -> None:
        """Receive events and refresh state until the client is closed.

        Reconnects with bounded backoff when the connection is lost, and
        reports panel communication through `on_availability_change`.
        """
        recv_task = self._start_receiving()
        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(
                self._update_loop(), name="nessclient update loop"
            )
        tasks = {recv_task, self._update_task}
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if not task.cancelled() and (error := task.exception()) is not None:
                    raise error
        finally:
            await self._cancel_tasks(tasks)

    async def _cancel_tasks(self, tasks: "set[asyncio.Task[None]]") -> None:
        current = asyncio.current_task()
        pending = [task for task in tasks if task is not current and not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def close(self) -> None:
        """Stop all background work and release the connection.

        Safe to call more than once, and after a failed connection attempt.
        """
        self._closed = True
        self._refresh_event.set()
        self._pulse_connection_event()
        await self._cancel_tasks(
            {task for task in (self._recv_task, self._update_task) if task is not None}
        )
        self._fail_pending_requests(ClientClosedError("Client is closed"))
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

    def on_availability_change(self, f: Callable[[bool], None]) -> Callable[[bool], None]:
        """Register a callback for changes in panel communication.

        Called with False when the connection is lost or the panel stops
        answering status requests, and with True once it answers again.
        """
        self._on_availability_change = f
        return f

    def on_aux_output_change(
        self, f: Callable[[int, bool], None]
    ) -> Callable[[int, bool], None]:
        self.alarm.on_aux_output_change(f)
        return f

    def stream_events(self) -> AsyncIterator[BaseEvent]:
        queue: asyncio.Queue[BaseEvent] = asyncio.Queue()
        self._event_subscribers.append(queue)

        async def _iterator() -> AsyncIterator[BaseEvent]:
            try:
                while True:
                    yield await queue.get()
            finally:
                self._event_subscribers.remove(queue)

        return _iterator()

    def stream_state_changes(
        self,
    ) -> AsyncIterator[tuple[ArmingState, ArmingMode | None]]:
        return self.alarm.stream_state_changes()

    def stream_zone_changes(self) -> AsyncIterator[tuple[int, bool]]:
        return self.alarm.stream_zone_changes()

    def stream_aux_output_changes(self) -> AsyncIterator[tuple[int, bool]]:
        return self.alarm.stream_aux_output_changes()
