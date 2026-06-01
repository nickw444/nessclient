import logging
import socket
import threading
import traceback
from typing import List, Callable, Any, Optional

from .zone import Zone
from ...event import BaseEvent, SystemStatusEvent
from ...packet import Packet, CommandType

_LOGGER = logging.getLogger(__name__)


class Server:
    def __init__(
        self,
        handle_command: Callable[[str], None],
        log_callback: Optional[Callable[[str], None]] = None,
        rx_callback: Optional[Callable[[str, Optional[Packet]], None]] = None,
    ):
        self._handle_command = handle_command
        self._log_callback = log_callback
        self._rx_callback = rx_callback
        self._handle_event_lock: threading.Lock = threading.Lock()
        self._clients_lock: threading.Lock = threading.Lock()
        self._clients: List[socket.socket] = []

    def start(self, host: str, port: int) -> None:
        self._stopflag = False
        self._server_accept_thread = threading.Thread(
            target=self._loop, args=(host, port), daemon=True, name="Server accept loop"
        )
        self._server_accept_thread.start()

    def stop(self) -> None:
        _LOGGER.debug("Stopping Server")
        self._stopflag = True
        self._server_accept_thread.join()

    def _disconnect_one_connection(self, conn: socket.socket) -> None:
        """Close a connection with a client."""
        _LOGGER.debug("Disconnecting client %s", conn)
        self._clients.remove(conn)
        if conn.fileno() != -1:
            try:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
            except OSError:
                _LOGGER.debug("Shutdown while already disconnected - ignore")

    def disconnect_all_clients(self) -> None:
        _LOGGER.debug("Server disconnecting all clients")
        for conn in self._clients:
            _LOGGER.debug(f"Disconnecting client {conn}")
            if conn.fileno() != -1:
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass  # not connected is fine
                conn.close()

    def _loop(self, host: str, port: int) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(5)
            s.settimeout(0.5)
            threadlist = []

            _LOGGER.info("Server listening on {}:{}".format(host, port))
            while not self._stopflag:
                try:
                    conn, addr = s.accept()
                except TimeoutError:
                    continue
                newthread = threading.Thread(
                    target=self._on_client_connected, args=(conn, addr), daemon=True
                )
                threadlist.append(newthread)
                newthread.start()
            s.close()
            self.disconnect_all_clients()
            for t in threadlist:
                _LOGGER.info(f"Server accept loop - waiting for {t} to end")
                t.join()
            _LOGGER.info("Server accept loop ended")

    def write_event(self, event: BaseEvent) -> None:
        pkt = event.encode()
        self._write_to_all_clients(pkt.encode())

    def on_zone_state_change(self, zone_id: int, state: Zone.State) -> None:
        event = SystemStatusEvent(
            type=get_zone_state_event_type(state),
            zone=zone_id,
            area=0,
            timestamp=None,
            address=0,
        )
        pkt = event.encode()
        self._write_to_all_clients(pkt.encode())

    def _on_client_connected(self, conn: socket.socket, addr: Any) -> None:
        _LOGGER.info("Client connected from: %s", addr)
        with self._clients_lock:
            self._clients.append(conn)

        buffer = b""
        try:
            while True:
                try:
                    data = conn.recv(1024)
                except OSError as e:
                    _LOGGER.info("Exception during recv: %s", e)
                    data = None
                if not data:
                    _LOGGER.info("client %s disconnected", addr)
                    break
                buffer += data
                # Process complete CRLF-terminated lines
                while True:
                    idx = buffer.find(b"\r\n")
                    if idx == -1:
                        break
                    line = buffer[:idx]
                    buffer = buffer[idx + 2 :]
                    line_str = line.decode("utf-8", errors="ignore")
                    if line_str:
                        self._handle_incoming_line(line_str)
        finally:
            with self._clients_lock:
                try:
                    self._clients.remove(conn)
                except ValueError:
                    pass
            try:
                conn.close()
            except Exception:
                pass

    def _write_to_all_clients(self, data: str) -> None:
        _LOGGER.debug("Writing message '%s' to all clients", data)
        with self._clients_lock:
            for conn in self._clients:
                conn.send(data.encode("utf-8") + b"\r\n")

    def _handle_incoming_line(self, line: str) -> None:
        _LOGGER.debug("Received incoming line: %s", line)
        try:
            pkt = Packet.decode(line)
            _LOGGER.debug("Packet is: %s", pkt)
            if self._rx_callback is not None:
                try:
                    self._rx_callback(line, pkt)
                except Exception:
                    _LOGGER.debug("rx_callback raised, ignoring", exc_info=True)
            # Handle Incoming Command:
            if (
                pkt.command == CommandType.USER_INTERFACE
                and not pkt.is_user_interface_resp
            ):
                _LOGGER.info("Handling User interface incoming: %s", pkt.data)
                with self._handle_event_lock:
                    self._handle_command(pkt.data)
            else:
                raise NotImplementedError()
        except Exception as e:
            msg = (
                f"Error decoding or handling line: {repr(line)}\n"
                f"{e}\n"
                f"{traceback.format_exc()}"
            )
            if self._rx_callback is not None:
                try:
                    self._rx_callback(line, None)
                except Exception:
                    _LOGGER.debug("rx_callback raised, ignoring", exc_info=True)
            if self._log_callback is not None:
                self._log_callback(msg)
            else:
                _LOGGER.exception("Failed to handle incoming line")


def get_zone_state_event_type(state: Zone.State) -> SystemStatusEvent.EventType:
    if state == Zone.State.SEALED:
        return SystemStatusEvent.EventType.SEALED
    if state == Zone.State.UNSEALED:
        return SystemStatusEvent.EventType.UNSEALED

    raise NotImplementedError()
