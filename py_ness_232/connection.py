import socket
from abc import ABC
from typing import Optional


class Connection(ABC):
    """Represents a connection to a Ness D8X/D16X server"""

    def read(self) -> Optional[bytes]:
        raise NotImplementedError()

    def write(self, data: bytes) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()


class IP232Connection(Connection):
    """A connection via IP232 with a Ness D8X/D16X server"""

    def __init__(self, host: str, port: int):
        super().__init__()

        self.__host = host
        self.__port = port
        self.__socket: Optional[socket.socket] = None

    def __connect(self) -> None:
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.connect((self.__host, self.__port))

    def read(self) -> Optional[bytes]:
        if self.__socket is None:
            self.__connect()
            assert self.__socket is not None

        data = self.__socket.recv(1024)
        if data is None:
            self.close()
            return None

        data = data.strip()
        if len(data) == 0:
            return None

        return data

    def write(self, data: bytes) -> None:
        if self.__socket is None:
            self.__connect()
            assert self.__socket is not None

        self.__socket.send(data)

    def close(self) -> None:
        if self.__socket is not None:
            self.__socket.close()
            self.__socket = None


class RS232Connection(Connection):
    """A connection via RS232 with a Ness D8X/D16X server"""

    def read(self) -> Optional[bytes]:
        pass

    def write(self, data: bytes) -> None:
        pass

    def close(self) -> None:
        pass
