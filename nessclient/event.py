"""Allows encoding and decoding of the payload of packets received from a Ness alarm."""

import datetime
import struct
from enum import Enum
from typing import TypeVar

from .packet import CommandType, Packet

T = TypeVar("T", bound=Enum)


def unpack_unsigned_short_data_enum(packet: Packet, enum_type: type[T]) -> list[T]:
    """
    Parse a bitfield from a 3 hex bytes of packet data.

    Returns a list of the bitfield enum items present.
    Used with bitfields of various StatusUpdate packet types
    """
    # Convert hex data to a byte array
    data = bytearray.fromhex(packet.data)

    # Parse a big-endian 16-bit value from the second and third bytes
    (raw_data,) = struct.unpack(">H", data[1:3])

    # Identify which bitfield items are represented by the value
    return [e for e in enum_type if e.value & raw_data]


def pack_unsigned_short_data_enum(items: list[T]) -> str:
    """
    Construct hex packet data from a list of bitfield items.

    Returns a 4-nibble hex value containing the bitfield enum items.
    Performs the reverse of unpack_unsigned_short_data_enum().

    Used with bitfields of various StatusUpdate packet types
    """
    # Construct an integer value containing all requested bitfield items
    value = 0
    for item in items:
        value |= item.value

    # Pack the value as a big-endian 16-bit byte array
    packed_value = struct.pack(">H", value)

    # Convert byte array to hex ready for insertion into a packet
    return packed_value.hex()


class BaseEvent(object):
    """
    Represents a message from a Ness alarm.

    BaseEvent represents a 'System Status Event' or a
    'Status Update User-Interface Response'
    received from the Ness alarm.
    """

    def __init__(
        self, address: int | None, timestamp: datetime.datetime | None
    ) -> None:
        """
        Construct a BaseEvent object - used by subclass constructors.

        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        self.address = address
        self.timestamp = timestamp

    def __repr__(self) -> str:
        """Get a string representation of the event."""
        return "<{} {}>".format(self.__class__.__name__, self.__dict__)

    @classmethod
    def decode(cls, packet: Packet) -> "BaseEvent":
        """
        Decode a packet from the Ness alarm.

        Decode a :py:class:`Packet` received from the
        Ness alarm into a :py:class:`BaseEvent` object
        Used by :py:meth:`_recv_loop`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`BaseEvent` object
        """
        if packet.command == CommandType.SYSTEM_STATUS:
            return SystemStatusEvent.decode(packet)
        elif packet.command == CommandType.USER_INTERFACE:
            return StatusUpdate.decode(packet)
        else:
            raise ValueError("Unknown command: {}".format(packet.command))

    def encode(self) -> Packet:
        """
        Abstract method - do not call.

        Provides a prototype for subclasses which can be encoded into
        a :py:class:`Packet`

        :return: The :py:class:`Packet` object representing this
                 encoded :py:class:`BaseEvent` object
        """
        raise NotImplementedError()


class SystemStatusEvent(BaseEvent):
    """
    SystemStatusEvent represents a 'System Status Event' received from the Ness alarm.

    These are asynchronous events indicating status changes.

    These are defined in part "1. Output Event Data" of:
    Ness D8x D16x Serial Interface - ASCII Protocol - v13
    """

    class EventType(Enum):
        """System Status Event types."""

        # Zone/User Events
        UNSEALED = 0x00
        SEALED = 0x01
        ALARM = 0x02
        ALARM_RESTORE = 0x03
        MANUAL_EXCLUDE = 0x04
        MANUAL_INCLUDE = 0x05
        AUTO_EXCLUDE = 0x06
        AUTO_INCLUDE = 0x07
        TAMPER_UNSEALED = 0x08
        TAMPER_NORMAL = 0x09

        # System Events
        POWER_FAILURE = 0x10
        POWER_NORMAL = 0x11
        BATTERY_FAILURE = 0x12
        BATTERY_NORMAL = 0x13
        REPORT_FAILURE = 0x14
        REPORT_NORMAL = 0x15
        SUPERVISION_FAILURE = 0x16
        SUPERVISION_NORMAL = 0x17
        REAL_TIME_CLOCK = 0x19

        # Area Events
        ENTRY_DELAY_START = 0x20
        ENTRY_DELAY_END = 0x21
        EXIT_DELAY_START = 0x22
        EXIT_DELAY_END = 0x23
        ARMED_AWAY = 0x24
        ARMED_HOME = 0x25
        ARMED_DAY = 0x26
        ARMED_NIGHT = 0x27
        ARMED_VACATION = 0x28
        ARMED_HIGHEST = 0x2E
        DISARMED = 0x2F
        ARMING_DELAYED = 0x30

        # Result Events
        OUTPUT_ON = 0x31
        OUTPUT_OFF = 0x32

    def __init__(
        self,
        type: "SystemStatusEvent.EventType",
        zone: int,
        area: int,
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`SystemStatusEvent` object - used by :py:meth:`decode`.

        :param type: The event type
        :param zone: The zone number associated with the event
                     (for zone based event types `UNSEALED` - `TAMPER_NORMAL`)
        :param area: The area number associated with the event
                     (for area based event types `ENTRY_DELAY_START` to
                     `ARMING_DELAYED`)
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        :param sequence: Indicates to set the 'sequence' bit - a bit that toggles
                         with each message received message from the Ness alarm
        """
        super(SystemStatusEvent, self).__init__(address=address, timestamp=timestamp)
        self.type = type
        self.zone = zone
        self.area = area

    @classmethod
    def decode(cls, packet: Packet) -> "SystemStatusEvent":
        """
        Decode a :py:class:`Packet` received from the Ness alarm.

        Decodes into a :py:class:`SystemStatusEvent` object
        Used by :py:meth:`BaseEvent.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`SystemStatusEvent` object
        """
        event_type = int(packet.data[0:2], 16)
        zone = int(packet.data[2:4])
        area = int(packet.data[4:6], 16)
        return SystemStatusEvent(
            type=SystemStatusEvent.EventType(event_type),
            zone=zone,
            area=area,
            timestamp=packet.timestamp,
            address=packet.address,
        )

    def encode(self) -> Packet:
        """
        Encode into a packet to send to a Ness alarm.

        Encodes this :py:class:`SystemStatusEvent` object into
        a :py:class:`Packet` object
        Note: Primarily for testing and simulating a Ness alarm

        :return: The :py:class:`Packet` object representing this
                 encoded :py:class:`SystemStatusEvent` object
        """
        data = "{:02x}{:02x}{:02x}".format(self.type.value, self.zone, self.area)
        return Packet(
            address=self.address,
            seq=0x00,
            command=CommandType.SYSTEM_STATUS,
            data=data,
            timestamp=None,
            is_user_interface_resp=False,
        )


class StatusUpdate(BaseEvent):
    """
    A Status update message from the Ness alarm.

    StatusUpdate represents a 'Status Update' message received from the
    Ness alarm in response to a 'Status Update User-Interface request'.
    These are synchronous response messages indicating current alarm status.
    """

    class RequestID(Enum):
        """The type of status update."""

        ZONE_INPUT_UNSEALED = 0x0
        ZONE_RADIO_UNSEALED = 0x1
        ZONE_CBUS_UNSEALED = 0x2
        ZONE_IN_DELAY = 0x3
        ZONE_IN_DOUBLE_TRIGGER = 0x4
        ZONE_IN_ALARM = 0x5
        ZONE_EXCLUDED = 0x6
        ZONE_AUTO_EXCLUDED = 0x7
        ZONE_SUPERVISION_FAIL_PENDING = 0x8
        ZONE_SUPERVISION_FAIL = 0x9
        ZONE_DOORS_OPEN = 0x10
        ZONE_DETECTOR_LOW_BATTERY = 0x11
        ZONE_DETECTOR_TAMPER = 0x12
        MISCELLANEOUS_ALARMS = 0x13
        ARMING = 0x14
        OUTPUTS = 0x15
        VIEW_STATE = 0x16
        PANEL_VERSION = 0x17
        AUXILIARY_OUTPUTS = 0x18

    def __init__(
        self,
        request_id: RequestID,
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`StatusUpdate` object - used by subclasses.

        :param request_id: The status update type
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(StatusUpdate, self).__init__(address=address, timestamp=timestamp)
        self.request_id = request_id

    @classmethod
    def decode(cls, packet: Packet) -> "StatusUpdate":
        """
        Decode a :py:class:`Packet` received from the Ness alarm.

        Decodes into a :py:class:`StatusUpdate` object
        Used by :py:meth:`BaseEvent.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`StatusUpdate` object
        """
        request_id = StatusUpdate.RequestID(int(packet.data[0:2], 16))
        if request_id.name.startswith("ZONE"):
            return ZoneUpdate.decode(packet)
        elif request_id == StatusUpdate.RequestID.MISCELLANEOUS_ALARMS:
            return MiscellaneousAlarmsUpdate.decode(packet)
        elif request_id == StatusUpdate.RequestID.ARMING:
            return ArmingUpdate.decode(packet)
        elif request_id == StatusUpdate.RequestID.OUTPUTS:
            return OutputsUpdate.decode(packet)
        elif request_id == StatusUpdate.RequestID.VIEW_STATE:
            return ViewStateUpdate.decode(packet)
        elif request_id == StatusUpdate.RequestID.PANEL_VERSION:
            return PanelVersionUpdate.decode(packet)
        elif request_id == StatusUpdate.RequestID.AUXILIARY_OUTPUTS:
            return AuxiliaryOutputsUpdate.decode(packet)
        else:
            raise ValueError("Unhandled request_id case: {}".format(request_id))


class ZoneUpdate(StatusUpdate):
    """
    A type of :py:class:`StatusUpdate` Status Update Packet (Output from Ness).

    Response to a User-Interface Status Request Packet
    Represents one of the 13 types of Status Update Packet that refer to zones
    """

    class Zone(Enum):
        """
        An enumeration representing a 2 byte Zone bitfield.

        Values listed in Form 4 of Ness D8x D16x Serial Interface - ASCII Protocol - v13
        """

        ZONE_1 = 0x0100
        ZONE_2 = 0x0200
        ZONE_3 = 0x0400
        ZONE_4 = 0x0800
        ZONE_5 = 0x1000
        ZONE_6 = 0x2000
        ZONE_7 = 0x4000
        ZONE_8 = 0x8000
        ZONE_9 = 0x0001
        ZONE_10 = 0x0002
        ZONE_11 = 0x0004
        ZONE_12 = 0x0008
        ZONE_13 = 0x0010
        ZONE_14 = 0x0020
        ZONE_15 = 0x0040
        ZONE_16 = 0x0080

    def __init__(
        self,
        included_zones: list[Zone],
        request_id: StatusUpdate.RequestID,
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`ZoneUpdate` object - used by py:meth:`decode`.

        :param included_zones: A list of Zones covered by the status update message
        :param request_id: The status update type
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(ZoneUpdate, self).__init__(
            request_id=request_id, address=address, timestamp=timestamp
        )
        self.included_zones = included_zones

    @classmethod
    def decode(cls, packet: Packet) -> "ZoneUpdate":
        """
        Decode a :py:class:`Packet` received from the Ness alarm.

        Decodes into a :py:class:`ZoneUpdate` object
        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`ZoneUpdate` object
        """
        request_id = StatusUpdate.RequestID(int(packet.data[0:2], 16))
        return ZoneUpdate(
            request_id=request_id,
            included_zones=unpack_unsigned_short_data_enum(packet, ZoneUpdate.Zone),
            timestamp=packet.timestamp,
            address=packet.address,
        )

    def encode(self) -> Packet:
        """
        Encode this :py:class:`ZoneUpdate` object into a :py:class:`Packet` object.

        Note: Primarily for testing and simulating a Ness alarm

        :return: The :py:class:`Packet` object representing this
                 encoded :py:class:`ZoneUpdate` object
        """
        data = "{:02x}{}".format(
            self.request_id.value,
            pack_unsigned_short_data_enum(self.included_zones),
        )
        return Packet(
            address=self.address,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data=data,
            timestamp=None,
            is_user_interface_resp=True,
        )


class MiscellaneousAlarmsUpdate(StatusUpdate):
    """
    Represents a MISCELLANEOUS_ALARMS 'System Status Event' received from a Ness alarm.

    These are synchronous response messages indicating current
    miscellaneous alarm status.
    """

    class AlarmType(Enum):
        """
        An enumeration representing a 2 byte Miscellaneous Alarms bitfield.

        Values listed in Form 20 of:
        "Ness D8x D16x Serial Interface - ASCII Protocol - v13"

        Note: The ness provided documentation has the byte endianness
        incorrectly documented. For this reason, these enum values have
        reversed byte ordering compared to the ness provided documentation.

        This only applies to some enums, and thus must be applied on a
        case-by-case basis
        """

        DURESS = 0x0100
        PANIC = 0x0200
        MEDICAL = 0x0400
        FIRE = 0x0800
        INSTALL_END = 0x1000
        EXT_TAMPER = 0x2000
        PANEL_TAMPER = 0x4000
        KEYPAD_TAMPER = 0x8000
        PENDANT_PANIC = 0x0001
        PANEL_BATTERY_LOW = 0x0002
        PANEL_BATTERY_LOW2 = 0x0004
        MAINS_FAIL = 0x0008
        CBUS_FAIL = 0x0010

    def __init__(
        self,
        included_alarms: list[AlarmType],
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`MiscellaneousAlarmsUpdate` object.

        - used by :py:meth:`decode`

        :param included_alarms: A list of active miscellaneous alarms
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(MiscellaneousAlarmsUpdate, self).__init__(
            request_id=StatusUpdate.RequestID.MISCELLANEOUS_ALARMS,
            address=address,
            timestamp=timestamp,
        )

        self.included_alarms = included_alarms

    @classmethod
    def decode(cls, packet: Packet) -> "MiscellaneousAlarmsUpdate":
        """
        Decode a Miscellaneous Alarms Update packet.

        Decode a :py:class:`Packet` received from the Ness alarm into
        a :py:class:`MiscellaneousAlarmsUpdate` object
        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`MiscellaneousAlarmsUpdate` object
        """
        return MiscellaneousAlarmsUpdate(
            included_alarms=unpack_unsigned_short_data_enum(
                packet, MiscellaneousAlarmsUpdate.AlarmType
            ),
            timestamp=packet.timestamp,
            address=packet.address,
        )


class ArmingUpdate(StatusUpdate):
    """
    Represents a ARMING 'System Status Event' received from the Ness alarm.

    These are synchronous response messages indicating arming mode status.
    """

    class ArmingStatus(Enum):
        """
        An enumeration representing a 2 byte Arming Status bitfield.

        This Bitfield represents the various armed states that can
        be enabled in the Ness Alarm
        An enumeration representing a 2 byte Arming Status bitfield
        Values from Form 21 of Ness D8x D16x Serial Interface - ASCII Protocol - v13
        """

        AREA_1_ARMED = 0x0100
        AREA_2_ARMED = 0x0200
        AREA_1_FULLY_ARMED = 0x0400
        AREA_2_FULLY_ARMED = 0x0800
        MONITOR_ARMED = 0x1000
        DAY_MODE_ARMED = 0x2000
        ENTRY_DELAY_1_ON = 0x4000
        ENTRY_DELAY_2_ON = 0x8000
        MANUAL_EXCLUDE_MODE = 0x0001
        MEMORY_MODE = 0x0002
        DAY_ZONE_SELECT = 0x0004

    def __init__(
        self,
        status: list["ArmingUpdate.ArmingStatus"],
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`ArmingUpdate` object.

        - used by :py:meth:`decode`

        :param status: A list of armed modes
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(ArmingUpdate, self).__init__(
            request_id=StatusUpdate.RequestID.ARMING,
            address=address,
            timestamp=timestamp,
        )

        self.status = status

    @classmethod
    def decode(cls, packet: Packet) -> "ArmingUpdate":
        """
        Decode a received ArmingUpdate 'System Status Event' packet.

        Decode a :py:class:`Packet` received from the Ness alarm
        into a :py:class:`ArmingUpdate` object
        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`ArmingUpdate` object
        """
        return ArmingUpdate(
            status=unpack_unsigned_short_data_enum(packet, ArmingUpdate.ArmingStatus),
            address=packet.address,
            timestamp=packet.timestamp,
        )

    def encode(self) -> Packet:
        """
        Encode this :py:class:`ArmingUpdate` object into a :py:class:`Packet` object.

        Note: Primarily for testing and simulating a Ness alarm

        :return: The :py:class:`Packet` object representing this
                 encoded :py:class:`ArmingUpdate` object
        """
        data = "{:02x}{}".format(
            self.request_id.value,
            pack_unsigned_short_data_enum(self.status),
        )
        return Packet(
            address=self.address,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data=data,
            timestamp=None,
            is_user_interface_resp=True,
        )


class OutputsUpdate(StatusUpdate):
    """
    Represents an OUTPUTS 'System Status Event' received from the Ness alarm.

    These are synchronous response messages indicating current state of all outputs
    """

    class OutputType(Enum):
        """
        An enumeration representing a 2 byte bitfield of all Outputs for the Ness alarm.

        An enumeration representing a 2 byte output state bitfield
        Values from Form 22 of Ness D8x D16x Serial Interface - ASCII Protocol - v13
        """

        SIREN_LOUD = 0x0100
        SIREN_SOFT = 0x0200
        SIREN_SOFT_MONITOR = 0x0400
        SIREN_SOFT_FIRE = 0x0800
        STROBE = 0x1000
        RESET = 0x2000
        SONALART = 0x4000
        KEYPAD_DISPLAY_ENABLE = 0x8000
        AUX1 = 0x0001
        AUX2 = 0x0002
        AUX3 = 0x0004
        AUX4 = 0x0008
        MONITOR_OUT = 0x0010
        POWER_FAIL = 0x0020
        PANEL_BATT_FAIL = 0x0040
        TAMPER_XPAND = 0x0080

    def __init__(
        self,
        outputs: list["OutputsUpdate.OutputType"],
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`OutputsUpdate` object - used by :py:meth:`decode`.

        :param outputs: A list of active outputs
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(OutputsUpdate, self).__init__(
            request_id=StatusUpdate.RequestID.OUTPUTS,
            address=address,
            timestamp=timestamp,
        )
        self.outputs = outputs

    @classmethod
    def decode(cls, packet: Packet) -> "OutputsUpdate":
        """
        Decode a received OutputsUpdate 'System Status Event' packet.

        Decode a :py:class:`Packet` received from the Ness alarm
        into a :py:class:`OutputsUpdate` object.

        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`OutputsUpdate` object
        """
        return OutputsUpdate(
            outputs=unpack_unsigned_short_data_enum(packet, OutputsUpdate.OutputType),
            timestamp=packet.timestamp,
            address=packet.address,
        )


class ViewStateUpdate(StatusUpdate):
    """
    Represents a VIEW_STATE type 'System Status Event' received from the Ness alarm.

    These are synchronous response messages indicating current
    'view state' that connected displays are in.
    """

    class State(Enum):
        """
        An enumeration representing a 2 byte bitfield of View States of the Ness alarm.

        This enumeration represents the different modes ('view states') that a
        display connected to the Ness alarm might have.
        This 2 byte output is NOT a bitfield.
        Values from Form 23 of Ness D8x D16x Serial Interface - ASCII Protocol - v13
        """

        NORMAL = 0xF000
        BRIEF_DAY_CHIME = 0xE000
        HOME = 0xD000
        MEMORY = 0xC000
        BRIEF_DAY_ZONE_SELECT = 0xB000
        EXCLUDE_SELECT = 0xA000
        USER_PROGRAM = 0x9000
        INSTALLER_PROGRAM = 0x8000

    def __init__(
        self,
        state: "ViewStateUpdate.State",
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`ViewStateUpdate` object - used by :py:meth:`decode`.

        :param state: The view state (current display mode)
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(ViewStateUpdate, self).__init__(
            request_id=StatusUpdate.RequestID.VIEW_STATE,
            address=address,
            timestamp=timestamp,
        )
        self.state = state

    @classmethod
    def decode(cls, packet: Packet) -> "ViewStateUpdate":
        """
        Decode a received VIEWS_TATE 'System Status Event' packet.

        Decode a :py:class:`Packet` received from the Ness alarm into
        a :py:class:`ViewStateUpdate` object.

        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`ViewStateUpdate` object
        """
        state = ViewStateUpdate.State(int(packet.data[2:6], 16))
        return ViewStateUpdate(
            state=state,
            timestamp=packet.timestamp,
            address=packet.address,
        )


class PanelVersionUpdate(StatusUpdate):
    """
    Represents a PANEL_VERSION type 'System Status Event' received from the Ness alarm.

    These are synchronous response messages indicating Ness Alarm model
    and currently running firmware version.
    """

    class Model(Enum):
        """
        Represents different Ness alarm models.

        Names & Values are as per Ness D8x D16x Serial Interface - ASCII Protocol - v13

        NOTE: D8X is not represented, but output 0x00
        """

        D16X = 0x00
        D16X_3G = 0x04
        D16XCEL = 0x14

    def __init__(
        self,
        model: Model,
        major_version: int,
        minor_version: int,
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`PanelVersionUpdate` object - used by :py:meth:`decode`.

        :param model: The Ness alarm model
        :param major_version: The major part of the firmware version number 0x0 to 0xf
        :param minor_version: The minor part of the firmware version number 0x0 to 0xf
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(PanelVersionUpdate, self).__init__(
            request_id=StatusUpdate.RequestID.PANEL_VERSION,
            address=address,
            timestamp=timestamp,
        )
        self.model = model
        self.major_version = major_version
        self.minor_version = minor_version

    @property
    def version(self) -> str:
        """Create a string representing the Ness alarm version number."""
        return "{}.{}".format(self.major_version, self.minor_version)

    @classmethod
    def decode(cls, packet: Packet) -> "PanelVersionUpdate":
        """
        Decode a received PANEL_VERSION 'System Status Event' packet.

        Decode a :py:class:`Packet` received from the Ness alarm into
        a :py:class:`PanelVersionUpdate` object
        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`PanelVersionUpdate` object
        """
        model = PanelVersionUpdate.Model(int(packet.data[2:4], 16))
        major_version = int(packet.data[4:5], 16)
        minor_version = int(packet.data[5:6], 16)
        return PanelVersionUpdate(
            model=model,
            minor_version=minor_version,
            major_version=major_version,
            timestamp=packet.timestamp,
            address=packet.address,
        )


class AuxiliaryOutputsUpdate(StatusUpdate):
    """
    Represents a AUXILIARY_OUTPUTS 'System Status Event' received from the Ness alarm.

    These are synchronous response messages indicating
    current state of all auxillary outputs
    """

    class OutputType(Enum):
        """
        A bitfield of all auxilliary outputs from the Ness alarm.

        An enumeration representing a 2 byte output state bitfield
        Values from Form 24 of Ness D8x D16x Serial Interface - ASCII Protocol - v13
        """

        AUX_1 = 0x0001
        AUX_2 = 0x0002
        AUX_3 = 0x0004
        AUX_4 = 0x0008
        AUX_5 = 0x0010
        AUX_6 = 0x0020
        AUX_7 = 0x0040
        AUX_8 = 0x0080

    def __init__(
        self,
        outputs: list[OutputType],
        address: int | None,
        timestamp: datetime.datetime | None,
    ) -> None:
        """
        Construct a :py:class:`AuxiliaryOutputsUpdate` object.

        - used by :py:meth:`decode`

        :param outputs: A list of the active auxilliary outputs
        :param address: The address of the Ness alarm: 0x0 to 0xf  (default is 0x0)
        :param timestamp: Optional timestamp for the event
        """
        super(AuxiliaryOutputsUpdate, self).__init__(
            request_id=StatusUpdate.RequestID.AUXILIARY_OUTPUTS,
            address=address,
            timestamp=timestamp,
        )
        self.outputs = outputs

    @classmethod
    def decode(cls, packet: Packet) -> "AuxiliaryOutputsUpdate":
        """
        Decode a received AUXILIARY_OUTPUTS 'System Status Event' packet.

        Decode a :py:class:`Packet` received from the Ness alarm into
        a :py:class:`AuxiliaryOutputsUpdate` object
        Used by :py:meth:`StatusUpdate.decode`

        :param packet: The packet that is to be decoded
        :return: The decode :py:class:`AuxiliaryOutputsUpdate` object
        """
        return AuxiliaryOutputsUpdate(
            outputs=unpack_unsigned_short_data_enum(
                packet, AuxiliaryOutputsUpdate.OutputType
            ),
            timestamp=packet.timestamp,
            address=packet.address,
        )
