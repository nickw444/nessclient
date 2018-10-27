from typing import Optional

from .connection import Connection, IP232Connection
from .event import BaseEvent
from .packet import CommandType, Packet


class Client:
    def __init__(self,
                 connection: Optional[Connection] = None,
                 host: Optional[str] = None,
                 port: Optional[int] = None):
        if connection is None:
            assert host is not None
            assert port is not None
            connection = IP232Connection(host, port)

        self.__connection = connection

    def send_command(self, command: str) -> None:
        packet = Packet.create(
            command=CommandType.USER_INTERFACE,
            start=0x83,
            address=0x00,
            data=command.encode('ascii'),
        )
        return self.__connection.write(packet.encode().encode('ascii'))

    def read_event(self) -> Optional[BaseEvent]:
        data = self.__connection.read()
        if data is not None:
            pkt = Packet.decode(data)
            return BaseEvent.decode(pkt)

        return None
