import logging
import socket
import threading
from typing import List, Callable

from .zone import Zone
from ...event import BaseEvent, SystemStatusEvent
from ...packet import Packet, CommandType

_LOGGER = logging.getLogger(__name__)


class Server:
    def __init__(self, handle_command: Callable[[str], None]):
        self._handle_command = handle_command
        self._handle_event_lock: threading.Lock = threading.Lock()
        self._clients_lock: threading.Lock = threading.Lock()
        self._clients: List[socket.socket] = []

    def start(self, host, port):
        threading.Thread(target=self._loop, args=(host, port)).start()

    def _loop(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(5)

            _LOGGER.info("Server listening on {}:{}".format(host, port))
            while True:
                conn, addr = s.accept()
                threading.Thread(
                    target=self._on_client_connected, args=(conn, addr)).start()

    def write_event(self, event: BaseEvent):
        pkt = event.encode()
        self._write_to_all_clients(pkt.encode())

    def on_zone_state_change(self, zone_id: int, state: Zone.State):
        event = SystemStatusEvent(
            type=get_zone_state_event_type(state),
            zone=zone_id,
            area=0,
            timestamp=None,
            address=0
        )
        pkt = event.encode()
        self._write_to_all_clients(pkt.encode())

    def _on_client_connected(self, conn: socket.socket, addr):
        _LOGGER.info("Client connected from: %s", addr)
        with self._clients_lock:
            self._clients.append(conn)

        while True:
            data = conn.recv(1024)
            if data is None or len(data) == 0:
                _LOGGER.info("client %s disconnected", addr)
                with self._clients_lock:
                    self._clients.remove(conn)

                break

            self._handle_incoming_data(data)

    def _write_to_all_clients(self, data: str):
        _LOGGER.debug("Writing message '%s' to all clients", data)
        with self._clients_lock:
            for conn in self._clients:
                conn.send(data.encode('utf-8') + b'\r\n')

    def _handle_incoming_data(self, data: bytes):
        _LOGGER.debug("Received incoming data: %s", data)
        pkt = Packet.decode(data.strip().decode('utf-8'))
        _LOGGER.debug("Packet is: %s", pkt)
        # Handle Incoming Command:
        if pkt.command == CommandType.USER_INTERFACE and not pkt.is_user_interface_resp:
            _LOGGER.info("Handling User interface incoming: %s", pkt.data)
            with self._handle_event_lock:
                self._handle_command(pkt.data)
        else:
            raise NotImplementedError()


def get_zone_state_event_type(state: Zone.State) -> SystemStatusEvent.EventType:
    if state == Zone.State.SEALED:
        return SystemStatusEvent.EventType.SEALED
    if state == Zone.State.UNSEALED:
        return SystemStatusEvent.EventType.UNSEALED

    raise NotImplementedError()
