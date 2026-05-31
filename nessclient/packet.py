r"""
Encode / Decode NESS Serial ASCII protocol packets.

Packets are ASCII encoded data.
    Packet layouts are similar but with important differences:

Input (to Ness) User-Interface Packet
Either a Keypad String or Status Request:
* Start:    2 upper case hex characters - must be "83"
* Address:  1 upper case hex character  - "0" to "F"
* Length:   2 upper case hex characters - must be "01" to "1E"
              - Note: it appears that values between 0xA-0xF do not work properly
* Command:  2 upper case hex characters - must be "60"
* Data:     N ascii characters - where N = Data Length field
              - must be from the set: "AHEXFVPDM*#0123456789S"
* Checksum: 2 upper case hex characters - hex( 0x100
              - (sum(ordinal of each hex character of previous fields) & 0xff))
* Finish:   2 characters "\r\n" (Carriage Return, Line Feed - CRLF)

Output (from Ness) Asynchronous Event Data Packet: (see SystemStatusEvent class)
* Start:    2 lower case hex characters - must be "82", "83", "86", "87"
* Address:  2 lower case hex characters - "00" to "0F"
              - only present in start mode "83" or "87"
* Length:   2 lower case hex characters - must be "03" or "83"
              - upper bit is alternating "Sequence"
* Command:  2 lower case hex characters - must be "61"
* Data:     6 lower case hex characters
              (double the length specified in the Length field)
* Timestamp: 12 ascii digit characters
              - "YYMMDDHHmmSS" - only present in start mode "86" or "87"
* Checksum: 2 lower case hex characters
              - sets the sum the integers that each hex pair
                represent to zero (excluding finish CRLF)
* Finish:   2 characters "\r\n" (Carriage Return, Line Feed - CRLF)

Output (from Ness) Status Update Packet:
    (Response to a User-Interface Status Request Packet) (see StatusUpdate class)
* Start:    2 lower case hex characters - must be "82"
* Address:  2 lower case hex characters - "00" to "0F"
              - Note: Address always present despite 0x82 start
                value that would normally indicate no-address.
* Length:   2 lower case hex characters - must be "03"
* Command:  2 lower case hex characters - must be "60"
* Data:     6 lower case hex characters
              (double the length specified in the Length field)
              - Note: Values have different meanings to Event Data Packet
* Checksum: 2 lower case hex characters
              - sets the sum the integers that each
                hex pair represent to zero (excluding finish CRLF)
* Finish:   2 characters "\r\n" (Carriage Return, Line Feed - CRLF)

"""

import datetime
import logging
from dataclasses import dataclass
from enum import Enum

_LOGGER = logging.getLogger(__name__)


class CommandType(Enum):
    """Ness Serial ASCII Protocol Command byte values."""

    SYSTEM_STATUS = 0x61
    USER_INTERFACE = 0x60


@dataclass
class Packet:
    """Represents a generic Ness Serial protocol packet."""

    address: int | None
    seq: int
    command: CommandType
    data: str
    timestamp: datetime.datetime | None

    USER_INTERFACE_RESPONSE_DATA_SIZE = 6  # 6 hex characters
    USER_INTERFACE_REQUEST_DATA_SIZE_MIN = 1
    USER_INTERFACE_REQUEST_DATA_SIZE_MAX = 30
    SYSTEM_STATUS_DATA_SIZE = 6  # 6 hex characters
    ADDRESS_MIN = 0x0
    ADDRESS_MAX = 0xF

    START_BYTE_ADDRESS_INCLUDED = 0x01
    START_BYTE_BASIC_HEADER = 0x02
    START_BYTE_TIMESTAMP_INCLUDED = 0x04
    START_BYTE_ASCII_FORMAT = 0x80

    USER_INTERFACE_REQUEST_FIXED_START_BYTE = 0x83
    USER_INTERFACE_RESPONSE_FIXED_START_BYTE = 0x82

    USER_INTERFACE_RESPONSE_ENCODED_LENGTH = 16

    VALID_UI_REQUEST_CHARACTERS = "AHEXFVPDM*#0123456789S"

    # Start:2, Length:1, Command:2, Checksum:2, Finish:2
    MINIMUM_PACKET_LENGTH = 7

    # Whether or not this packet is a USER_INTERFACE response
    is_user_interface_resp: bool = False

    # Input Packets can have a command separator delay marker
    # This is a "?" character after the checksum
    has_delay_marker: bool = False

    def __init__(  # noqa: PLR0913 # Cannot reduce arguments without changing API
        self,
        *,
        command: CommandType,
        data: str,
        address: int | None = None,
        seq: int = 0,
        timestamp: datetime.datetime | None = None,
        is_user_interface_resp: bool = False,
        has_delay_marker: bool = False,
    ) -> None:
        """
        Create a packet object.

        Users will call this to create a packet ready for encoding/sending.

        Internally it is called by decode() to create the decoded packet.
        """
        # These checks raise a ValueError if details are invalid
        if command == CommandType.USER_INTERFACE:
            if is_user_interface_resp:
                # Output (from Ness) Status Update Packet:
                # (Response to a User-Interface Status Request Packet)
                Packet._check_ui_response(
                    data, address, seq, timestamp, has_delay_marker=has_delay_marker
                )
            else:
                # Input (to Ness) User-Interface (Request) Packet:
                Packet._check_ui_request(data, address, seq, timestamp)
        elif command == CommandType.SYSTEM_STATUS:
            # Output (from Ness) Event Data Packet: (see SystemStatusEvent class)
            Packet._check_event_packet(data, has_delay_marker=has_delay_marker)
        else:
            msg = f"Unknown command {command}"
            raise ValueError(msg)

        if address is not None and (
            address < Packet.ADDRESS_MIN or address > Packet.ADDRESS_MAX
        ):
            msg = (
                f"Address must be in the range {Packet.ADDRESS_MIN}"
                f"- {Packet.ADDRESS_MAX} if provided - got {address}"
            )
            raise ValueError(msg)

        # Validated
        self.command = command
        self.data = data
        self.address = address
        self.seq = seq
        self.timestamp = timestamp
        self.is_user_interface_resp = is_user_interface_resp
        self.has_delay_marker = has_delay_marker

    @staticmethod
    def _check_ui_response(
        data: str,
        address: int | None,
        seq: int,
        timestamp: datetime.datetime | None,
        *,
        has_delay_marker: bool,
    ) -> None:
        # Check details of a UI response packet - raise exception if invalid
        # Output (from Ness) Status Update Packet
        # (Response to a User-Interface Status Request Packet)

        if len(data) != Packet.USER_INTERFACE_RESPONSE_DATA_SIZE:
            msg = (
                "Data length of a User-Interface status "
                f"update response must be 6 - got {len(data)}"
            )
            raise ValueError(msg)
        if not Packet._is_hex(data):
            msg = (
                "Data of a User-Interface status update "
                f"response must be hex - got {data}"
            )
            raise ValueError(msg)
        if address is None:
            msg = (
                "User-Interface status update responses "
                f"must have an address - got {address}"
            )
            raise ValueError(msg)
        if timestamp is not None:
            msg = (
                "User-Interface status update responses "
                f"must not have a timestamp - got {timestamp}"
            )
            raise ValueError(msg)
        if seq != 0:
            msg = (
                "User-Interface status update responses do "
                f"not use sequence - it must be zero - got {seq}"
            )
            raise ValueError(msg)
        if has_delay_marker:
            msg = "User-Interface status update responses do not use delay markers"
            raise ValueError(msg)

    @staticmethod
    def _check_ui_request(
        data: str, address: int | None, seq: int, timestamp: datetime.datetime | None
    ) -> None:
        # Check details of a UI request packet - raise exception if invalid
        # Input (to Ness) User-Interface (Request) Packet:
        # (A User-Interface Status Request Packet)
        if (
            len(data) < Packet.USER_INTERFACE_REQUEST_DATA_SIZE_MIN
            or len(data) > Packet.USER_INTERFACE_REQUEST_DATA_SIZE_MAX
        ):
            msg = (
                "Data length of a User-Interface Packet must be in the range "
                f"{Packet.USER_INTERFACE_REQUEST_DATA_SIZE_MIN}"
                f" - {Packet.USER_INTERFACE_REQUEST_DATA_SIZE_MAX}"
                f" - got {len(data)}"
            )
            raise ValueError(msg)
        if not Packet._is_valid_ui_data_char(data):
            msg = (
                "Data characters of a User-Interface Packet must "
                f"be one of 'AHEXFVPDM*#01234567890S' - got {data}"
            )
            raise ValueError(msg)
        if address is None:
            msg = f"User-Interface Packet must have an address - got {address}"
            raise ValueError(msg)
        if timestamp is not None:
            msg = f"User-Interface Packet must not have a timestamp - got {timestamp}"
            raise ValueError(msg)
        if seq != 0:
            msg = (
                f"User-Interface Packet do not use sequence - it must be zero - got {seq}"
            )
            raise ValueError(msg)

    @staticmethod
    def _check_event_packet(
        data: str,
        *,
        has_delay_marker: bool,
    ) -> None:
        # Check details of a UI request packet - raise exception if invalid
        # Input (to Ness) User-Interface (Request) Packet:
        # (A User-Interface Status Request Packet)
        # Output (from Ness) Event Data Packet: (see SystemStatusEvent class)
        if len(data) != Packet.SYSTEM_STATUS_DATA_SIZE:
            msg = (
                "Data length of a System Status Event Data Packet "
                f"must be {Packet.SYSTEM_STATUS_DATA_SIZE} - got {len(data)}"
            )
            raise ValueError(msg)
        if not Packet._is_hex(data):
            msg = f"Data of a System Status Event Data Packet must be hex - got {data}"
            raise ValueError(msg)
        if has_delay_marker:
            msg = "System Status Event Data Packet must not use delay markers"
            raise ValueError(msg)

    @staticmethod
    def _is_hex(s: str) -> bool:
        """Return True if the supplied string is entirely valid hexidecimal chars."""
        return all(c in "0123456789ABCDEFabcdef" for c in s)

    @staticmethod
    def _is_valid_ui_data_char(s: str) -> bool:
        """Return True if the supplied string is valid NESS UI data characters."""
        return all(c in Packet.VALID_UI_REQUEST_CHARACTERS for c in s)

    @property
    def start(self) -> int:
        """
        Return START-byte for this packet.

        The start byte is:
            * Input-to-Ness UI Request - Always 0x83
            * Output-from-Ness UI Response - Always 0x82
            * Output-from-Ness Asynchronous Event Data -
                        0x82, 0x83, 0x86, 0x87 according to table in specification
        """
        # Basic-Header and ASCII-Format are always present
        start_byte = Packet.START_BYTE_BASIC_HEADER | Packet.START_BYTE_ASCII_FORMAT
        if self.address is not None and not self.is_user_interface_resp:
            start_byte |= Packet.START_BYTE_ADDRESS_INCLUDED
        if self.timestamp is not None:
            start_byte |= Packet.START_BYTE_TIMESTAMP_INCLUDED

        return start_byte

    @property
    def length_field(self) -> int:
        """
        Return LENGTH-byte for this packet.

        The length byte is:
            * Input-to-Ness UI Request - 1 to 30 (0x01 to 0x1e) inclusive
            * Output-from-Ness UI Response - Always 0x03
            * Output-from-Ness Asynchronous Event Data -
                The length byte a combination of the sequence bit and the packet length
                Always 0x03 or 0x83
        """
        return int(self.length) | (self.seq << 7)

    @property
    def length(self) -> int:
        """Return data length value for this packet."""
        if _is_user_interface_req(self.start, self.command):
            return len(self.data)

        return int(len(self.data) / 2)

    @property
    def checksum(self) -> int:
        """Return checksum value for this packet."""
        data_bytes = self.encode(with_checksum=False).strip()

        # Checksum is calculated differently depending on the packet type.
        if _is_user_interface_req(self.start, self.command):
            # Input (to Ness) User-Interface Packets sum the
            # ordinal of each hex character, excluding the checksum and CRLF
            # e.g. '8300360S00E9\r\n'
            #      Sum = 0x38 + 0x33 + 0x30 + 0x30 + 0x33 +
            #            0x36 + 0x30 + 0x53 + 0x30 + 0x30 = 0x217
            #      Checksum = (-Sum) & 0xff = 0xE9
            total = sum([ord(x) for x in data_bytes])
        else:
            # Output (from Ness) System-Status Packets sum the
            # integers that each hex pair represent, excluding the checksum and CRLF
            # e.g. '820003600000001b\r\n'
            #      Sum = 0x82 + 0x00 + 0x03 + 0x60 + 0x00 + 0x00 + 0x00 = 0xE5
            #      Checksum = (-Sum) & 0xff = 0x1b
            total = 0
            for pos in range(0, len(data_bytes), 2):
                total += int(data_bytes[pos : pos + 2], 16)

        return (256 - total) % 256

    def encode(self, *, with_checksum: bool = True) -> str:
        """Encode this packet to a Ness Serial ASCII Protocol string."""
        data = ""
        data += f"{self.start:02x}"

        if self.address is not None:
            if _is_user_interface_req(self.start, self.command):
                # Request address should be upper case
                # according to D8-D16SerialInterface.exe
                data += f"{self.address:01X}"
            else:
                data += f"{self.address:02x}"

        if _is_user_interface_req(self.start, self.command):
            # Request length & command should be upper case
            # according to D8-D16SerialInterface.exe
            data += f"{self.length_field:02X}{self.command.value:02X}"
        else:
            data += f"{self.length_field:02x}{self.command.value:02x}"
        data += self.data

        if self.timestamp is not None:
            data += self.timestamp.strftime("%y%m%d%H%M%S")

        if with_checksum:
            checksum_str = f"{self.checksum:02x}"
            if _is_user_interface_req(self.start, self.command):
                # NOTE: Checksum for UI Input Request packets MUST be upper case
                #       Otherwise packets will be ignored by NESS
                data += checksum_str.upper()
            else:
                data += checksum_str

            data += "?" if self.has_delay_marker else ""

        return data

    @classmethod
    def decode(  # noqa: PLR0912, PLR0915 # Not easy to reduce complexity of this
        cls, _data: str
    ) -> "Packet":
        """
        Decode from a Ness Serial ASCII Protocol string into a Packet.

        Packets are ASCII encoded data. Packet layout is as follows.

        +---------------------------------------------------------------------------+
        | start | address | length | command | data | timestamp | checksum | finish |
        | hex   | hex     | hex    | hex     | str  | dec       | hex      | crlf   |
        | 1     | 1       | 1      | 1       | n    | 6         | 1        |        |
        +---------------------------------------------------------------------------+

        Timestamp:
            Timestamps are formatted in the following format, where each field is
            decimal encoded:

            YY MM DD HH MM SS

        Checksum:
            TODO: Calculated by...?

        Since data is ASCII encoded, each byte uses 2 ASCII character to be
        represented. However, we cannot simply do a hex decode on the entire
        message, since the timestamp and data fields are represented using a
        non-hex representation and therefore must be manually decoded.
        """
        # Check minimum data size
        if len(_data) < Packet.MINIMUM_PACKET_LENGTH:
            msg = f"Packet data too short : {_data!r}"
            raise ValueError(msg)

        has_delay_marker = False

        # Decoding of Length requires knowledge of the packet type, which
        # normally is specified by the start byte and command type.
        # Since the command cannot be decoded until after the length
        # there is a circular dependency
        # Instead, identify packet type via the position of the command byte
        # Input (to Ness) User-Interface Packet always have command 60 at position 5
        # Output packets always have command 61 at position 4 or 6
        is_input_ui_req = _data[5:7] == "60"
        if is_input_ui_req:
            # Input (to Ness) User-Interface Packet

            # Input Packets can have a command separator delay marker
            # Check for, and remove the delay marker
            if _data.endswith("?"):
                _data = _data[:-1]
                has_delay_marker = True

            # Input (to Ness) User-Interface Packets sum the
            # ordinal of each hex character, excluding the checksum and CRLF
            # e.g. '8300360S00E9\r\n'
            #      Sum = 0x38 + 0x33 + 0x30 + 0x30 + 0x33 +
            #            0x36 + 0x30 + 0x53 + 0x30 + 0x30 = 0x217
            #      Checksum = 0x100 - (Sum & 0xff) = 0xE9
            datasum = sum([ord(x) for x in _data[:-2]])
            try:
                checksum = int(_data[-2:], 16)
            except ValueError as e:
                msg = f"Invalid non-hex character in checksum byte: {_data!r}"
                raise ValueError(msg) from e
            if not _data.endswith(f"{checksum:02X}"):
                msg = f"Packet checksum for input request must be upper case : {_data!r}"
                raise ValueError(msg)
            if ((-datasum) & 0xFF) != checksum:
                msg = (
                    f"Packet checksum does not match : {_data!r} : "
                    f"0x{((-datasum) & 0xFF):02X} != 0x{checksum:02X}"
                )
                raise ValueError(msg)

        else:
            # Output (from Ness) System-Status Packet
            # or
            # Output (from Ness) Status Update Packet
            #    (Response to a User-Interface Status Request Packet)

            # Output packets sum the integers that each hex pair
            # represent, excluding the checksum and CRLF
            # e.g. '820003600000001b\r\n'
            #      Sum = 0x82 + 0x00 + 0x03 + 0x60 + 0x00 + 0x00 + 0x00 = 0xE5
            #      Checksum = 0x100 - (Sum & 0xff) = 0x1b
            datasum = 0
            for pos in range(0, len(_data), 2):
                try:
                    datasum += int(_data[pos : pos + 2], 16)
                except ValueError as e:
                    msg = f"Invalid non-hex character in data: {_data!r}"
                    raise ValueError(msg) from e

            if (datasum & 0xFF) != 0:
                expected_checksum = 0x100 - (
                    (datasum - int(_data[len(_data) - 2 : len(_data)], 16)) & 0xFF
                )
                msg = (
                    f"Packet checksum does not match : {_data!r} "
                    f"expecting checksum: 0x{expected_checksum:02X}"
                )
                raise ValueError(msg)

        data = DataIterator(_data)
        _LOGGER.debug("Decoding bytes: '%s'", _data)

        start = data.take_byte_value()

        address = None
        if _has_address(start, len(_data)):
            address = data.take_byte_value(hex_format=not is_input_ui_req)

        length = data.take_byte_value()
        data_length = length & 0x7F
        seq = length >> 7
        command = CommandType(data.take_byte_value())
        msg_data = data.take_bytes(data_length, hex_format=not is_input_ui_req)
        timestamp = None
        if bool(Packet.START_BYTE_TIMESTAMP_INCLUDED & start):
            timestamp = _decode_timestamp(data.take_bytes(6, hex_format=True))

        data.take_byte_value()  # Checksum has already been validated - just take it

        if not data.is_consumed():
            msg = "Unable to consume all data"
            raise ValueError(msg)

        is_user_interface_resp = (
            start == Packet.USER_INTERFACE_RESPONSE_FIXED_START_BYTE
            and command == CommandType.USER_INTERFACE
        )

        return Packet(
            is_user_interface_resp=is_user_interface_resp,
            address=address,
            seq=seq,
            command=command,
            data=msg_data,
            timestamp=timestamp,
            has_delay_marker=has_delay_marker,
        )


class DataIterator:
    """Data Buffer that allows taking incremental byte amounts."""

    def __init__(self, data: str) -> None:
        """Create a DataIterator with a specified string."""
        self._data = data
        self._position = 0

    def take_bytes(self, n: int, *, hex_format: bool = False) -> str:
        """
        Take bytes from the buffer, advancing the read position.

        If hex_format is specified, two bytes will be read for each
        requested
        """
        multi = 2 if hex_format else 1
        position = self._position
        self._position += n * multi
        if self._position > len(self._data):
            msg = "Unable to take more data than exists"
            raise ValueError(msg)

        return self._data[position : self._position]

    def take_byte_value(self, *, hex_format: bool = True) -> int:
        """Return an integer represented by 1 byte or 2 hex nibble characters."""
        return int(self.take_bytes(1, hex_format=hex_format), 16)

    def is_consumed(self) -> bool:
        """Return True if entire buffer has been read."""
        return self._position >= len(self._data)


def _has_address(start: int, data_length: int) -> bool:
    """
    Determine whether the packet has an "address" encoded into it.

    There exists an undocumented bug/edge case in the spec - some packets
    with 0x82 as _start_, still encode the address into the packet, and thus
    throws off decoding. This edge case is handled explicitly.
    """
    return bool(Packet.START_BYTE_ADDRESS_INCLUDED & start) or (
        start == Packet.USER_INTERFACE_RESPONSE_FIXED_START_BYTE
        and data_length == Packet.USER_INTERFACE_RESPONSE_ENCODED_LENGTH
    )


def _is_user_interface_req(start: int, command: CommandType) -> bool:
    return (
        start == Packet.USER_INTERFACE_REQUEST_FIXED_START_BYTE
        and command == CommandType.USER_INTERFACE
    )


def _decode_timestamp(data: str) -> datetime.datetime:
    """
    Decode timestamp using bespoke decoder.

    Cannot use simple strptime since the ness panel contains a bug
    that P199E zone and state updates emitted on the hour cause a minute
    value of `60` to be sent, causing strptime to fail. This decoder handles
    this edge case.
    """
    seconds_in_minute = 60

    year = 2000 + int(data[0:2])
    month = int(data[2:4])
    day = int(data[4:6])
    hour = int(data[6:8])
    minute = int(data[8:10])
    second = int(data[10:12])
    if minute == seconds_in_minute:
        minute = 0
        hour += 1

    return datetime.datetime(  # noqa: DTZ001 - local timezone - No function available
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
    )
