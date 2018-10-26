import datetime
import struct
from builtins import bytes
from enum import Enum
from typing import List, Optional, TypeVar

from .packet import CommandType, Packet

T = TypeVar('T', bound=Enum)


def unpack_unsigned_short_data_enum(packet: Packet, enum_type: T) -> List[T]:
    (raw_data,) = struct.unpack('>H', packet.data[1:3])
    return [e for e in enum_type if e.value & raw_data]


class BaseEvent(object):
    def __init__(self, packet: Packet):
        super(BaseEvent, self).__init__()
        self.address: Optional[int] = packet.address
        self.timestamp = None
        if packet.timestamp is not None:
            self.timestamp = BaseEvent.decode_timestamp(packet.timestamp)

    def __repr__(self) -> str:
        return '<{} {}>'.format(self.__class__.__name__, self.__dict__)

    @classmethod
    def decode_timestamp(cls, data: bytes) -> datetime.datetime:
        # Timestamp is a special snowflake - it is received as raw decimal ASCII
        # rather than encoded hex. We must convert it back to decimal in order to
        # decode it.
        decimal = data.hex()
        return datetime.datetime.strptime(decimal, '%y%m%d%H%M%S')

    @classmethod
    def decode(cls, packet: Packet) -> 'BaseEvent':
        if packet.command == CommandType.SYSTEM_STATUS:
            return SystemStatusEvent.decode(packet)
        elif packet.command == CommandType.USER_INTERFACE:
            return StatusUpdate.decode(packet)
        else:
            raise ValueError("Unknown command: {}".format(packet.command))


class SystemStatusEvent(BaseEvent):
    class EventType(Enum):
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
        ARMED_HIGHEST = 0x2e
        DISARMED = 0x2f
        ARMING_DELAYED = 0x30

        # Result Events
        OUTPUT_ON = 0x31
        OUTPUT_OFF = 0x32

    def __init__(self, packet: Packet):
        super(SystemStatusEvent, self).__init__(packet)
        self.type: SystemStatusEvent.EventType = SystemStatusEvent.EventType(
            packet.data[0])
        self.id: int = packet.data[1]
        self.area: int = packet.data[2]

    @classmethod
    def decode(cls, packet: Packet) -> 'SystemStatusEvent':
        return SystemStatusEvent(packet)


class StatusUpdate(BaseEvent):
    class RequestID(Enum):
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

    def __init__(self, packet: Packet):
        super(StatusUpdate, self).__init__(packet)

    @classmethod
    def decode(self, packet: Packet) -> 'StatusUpdate':
        request_id = StatusUpdate.RequestID(packet.data[0])
        if request_id.name.startswith('ZONE'):
            return ZoneUpdate(packet)
        elif request_id == StatusUpdate.RequestID.MISCELLANEOUS_ALARMS:
            return MiscellaneousAlarmsUpdate(packet)
        elif request_id == StatusUpdate.RequestID.ARMING:
            return ArmingUpdate(packet)
        elif request_id == StatusUpdate.RequestID.OUTPUTS:
            return OutputsUpdate(packet)
        elif request_id == StatusUpdate.RequestID.VIEW_STATE:
            return ViewStateUpdate(packet)
        else:
            raise ValueError("Unhandled request_id case: {}".format(request_id))


class ZoneUpdate(StatusUpdate):
    class Zone(Enum):
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

    def __init__(self, packet: Packet):
        super(ZoneUpdate, self).__init__(packet)

        self.id = StatusUpdate.RequestID(packet.data[0])
        (zones,) = struct.unpack('>H', packet.data[1:3])
        print("Zones", zones)
        self.included_zones: List[ZoneUpdate.Zone] = [
            z for z in ZoneUpdate.Zone if z.value & zones]


class MiscellaneousAlarmsUpdate(StatusUpdate):
    class AlarmType(Enum):
        DURESS = 0x0001
        PANIC = 0x0002
        MEDICAL = 0x0004
        FIRE =0x0008
        INSTALL_END = 0x0010
        EXT_TAMPER = 0x0020
        PANEL_TAMPER = 0x0040
        KEYPAD_TAMPER = 0x0080
        PENDANT_PANIC = 0x0100
        PANEL_BATTERY_LOW = 0x0200
        PANEL_BATTERY_LOW2 = 0x0400
        MAINS_FAIL = 0x0800
        CBUS_FAIL = 0x1000

    def __init__(self, packet: Packet):
        super(MiscellaneousAlarmsUpdate, self).__init__(packet)

        self.included_alarms: List[MiscellaneousAlarmsUpdate.AlarmType] = unpack_unsigned_short_data_enum(
            packet, MiscellaneousAlarmsUpdate.AlarmType)


class ArmingUpdate(StatusUpdate):
    class ArmingStatus(Enum):
        AREA_1_ARMED = 0x0001
        AREA_2_ARMED = 0x0002
        AREA_1_FULLY_ARMED = 0x0004
        AREA_2_FULLY_ARMED = 0x0008
        MONITOR_ARMED = 0x0010
        DAY_MODE_ARMED = 0x0020
        ENTRY_DELAY_1_ON = 0x0040
        ENTRY_DELAY_2_ON = 0x0080
        MANUAL_EXCLUDE_MODE = 0x0100
        MEMORY_MODE = 0x0200
        DAY_ZONE_SELECT = 0x0400

    def __init__(self, packet: Packet):
        super(ArmingUpdate, self).__init__(packet)

        self.status: List[ArmingUpdate.ArmingStatus] = unpack_unsigned_short_data_enum(
            packet, ArmingUpdate.ArmingStatus)


class OutputsUpdate(StatusUpdate):
    class OutputType(Enum):
        SIREN_LOUD = 0x0001
        SIREN_SOFT = 0x0002
        SIREN_SOFT_MONITOR = 0x0004
        SIREN_SOFT_FIRE = 0x0008
        STROBE = 0x0010
        RESET = 0x0020
        SONALART = 0x0040
        KEYPAD_DISPLAY_ENABLE = 0x0080
        AUX1 = 0x0100
        AUX2 = 0x0200
        AUX3 = 0x0400
        AUX4 = 0x0800
        MONITOR_OUT = 0x1000
        POWER_FAIL = 0x2000
        PANEL_BATT_FAIL = 0x4000
        TAMPER_XPAND = 0x8000

    def __init__(self, packet: Packet):
        super(OutputsUpdate, self).__init__(packet)

        self.outputs: List[OutputsUpdate.OutputType] = unpack_unsigned_short_data_enum(
            packet, OutputsUpdate.OutputType)


class ViewStateUpdate(StatusUpdate):
    class State(Enum):
        NORMAL = 0xf000
        BRIEF_DAY_CHIME = 0xe000
        HOME = 0xd000
        MEMORY = 0xc000
        BRIEF_DAY_ZONE_SELECT = 0xb000
        EXCLUDE_SELECT = 0xa000
        USER_PROGRAM = 0x9000
        INSTALLER_PROGRAM = 0x8000

    def __init__(self, packet: Packet):
        super(ViewStateUpdate, self).__init__(packet)

        (state,) = struct.unpack('>H', packet.data[1:3])
        self.state = ViewStateUpdate.State(state)
