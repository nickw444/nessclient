from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommandType(Enum):
    SYSTEM_STATUS = 0x61
    USER_INTERFACE = 0x60


@dataclass
class Packet:
    start: int
    address: Optional[int]
    seq: int
    command: CommandType
    data: bytes
    timestamp: Optional[bytes]

    @classmethod
    def verify_checksum(cls, data: bytes) -> None:
        checksum = 0
        for byte in data:
            checksum += byte

        if checksum & 0xff != 0:
            raise ValueError("Packet cannot be decoded - checksum verification failed.")

    @classmethod
    def create(cls, start: int, address: int, data: bytes, command: CommandType) -> 'Packet':
        return Packet(
            start=start,
            address=address,
            seq=0x00,
            command=command,
            data=data,
            timestamp=None,
        )

    def encode(self, with_checksum: bool = True) -> str:
        data = ''
        data += '{:02x}'.format(self.start)
        data += '{:01x}'.format(self.address)
        data += '{:02x}'.format(self.length)
        data += '{:02x}'.format(self.command.value)
        data += self.data.decode('ascii')

        if with_checksum:
            data += '{:02x}'.format(self.checksum)

        return data.upper()

    @property
    def length(self) -> int:
        return len(self.data)

    @property
    def checksum(self) -> int:
        bytes = self.encode(with_checksum=False)
        total = sum([ord(x) for x in bytes]) & 0xff
        return 256 - total

    @classmethod
    def decode(self, data: bytes) -> 'Packet':
        data = bytearray.fromhex(data.decode('ascii'))
        Packet.verify_checksum(data)

        start = data[0]
        has_address = bool(0x01 & start) or start == 0x82
        has_timestamp = bool(0x04 & start)

        address_len = 1 if has_address else 0
        timestamp_len = 6 if has_timestamp else 0
        data_len = data[address_len + 1] & 0x7f
        seq = data[address_len + 1] >> 7
        # assert data_len == 3

        return Packet(
            start=start,
            address=data[1] if has_address else None,
            seq=seq,
            command=CommandType(data[address_len + 2]),
            data=data[address_len + 3:address_len + 3 + data_len],
            timestamp=data[
                      address_len + 3 + data_len:address_len + 3 + data_len + timestamp_len] if has_timestamp else None,
        )

