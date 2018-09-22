import datetime
from builtins import bytes
from enum import Enum
from typing import List

from .packet import CommandType, Packet


class BaseEvent(object):
    def __init__(self, packet: Packet):
        super(BaseEvent, self).__init__()
        self.address: int = packet.address
        self.timestamp = None
        if packet.timestamp is not None:
            self.timestamp = BaseEvent.decode_timestamp(packet.timestamp)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.__dict__)

    @classmethod
    def decode_timestamp(cls, data: bytes):
        # Timestamp is a special snowflake - it is received as raw decimal ASCII
        # rather than encoded hex. We must convert it back to decimal in order to
        # decode it.
        decimal = data.hex()
        return datetime.datetime.strptime(decimal, '%y%m%d%H%M%S')

    @classmethod
    def decode(cls, packet: Packet):
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

    def __init__(self, packet: Packet):
        super(SystemStatusEvent, self).__init__(packet)
        self.type: SystemStatusEvent.EventType = SystemStatusEvent.EventType(packet.data[0])
        self.id: int = packet.data[1]
        self.area: int = packet.data[2]

    @classmethod
    def decode(cls, packet: Packet):
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
    def decode(self, packet: Packet):
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
    def __init__(self, packet: Packet):
        super(ZoneUpdate, self).__init__(packet)

        self.id = StatusUpdate.RequestID(packet.data[0])
        # TODO: Use bytes 1 + 2 to find zone numbers included.
        self.included_zones: List[int] = []


class MiscellaneousAlarmsUpdate(StatusUpdate):
    class AlarmType(Enum):
        DURESS = ''
        PANIC = ''
        MEDICAL = ''
        FIRE = ''
        INSTALL_END = ''
        EXT_TAMPER = ''
        PANEL_TAMPER = ''
        KEYPAD_TAMPER = ''
        PENDANT_PANIC = ''
        PANEL_BATTERY_LOW = ''
        PANEL_BATTERY_LOW2 = ''
        MAINS_FAIL = ''
        CBUS_FAIL = ''

    def __init__(self, packet: Packet):
        super(MiscellaneousAlarmsUpdate, self).__init__(packet)

        self.included_alarms: List[MiscellaneousAlarmsUpdate.AlarmType] = []


class ArmingUpdate(StatusUpdate):
    class ArmingStatus(Enum):
        AREA_1_ARMED = ''
        AREA_2_ARMED = ''
        AREA_1_FULLY_ARMED = ''
        AREA_2_FULLY_ARMED = ''
        MONITOR_ARMED = ''
        DAY_MODE_ARMED = ''
        ENTRY_DELAY_1_ON = ''
        ENTRY_DELAY_2_ON = ''
        MANUAL_EXCLUDE_MODE = ''
        MEMORY_MODE = ''
        DAY_ZONE_SELECT = ''

    def __init__(self, packet: Packet):
        super(ArmingUpdate, self).__init__(packet)

        self.status: List[ArmingUpdate.ArmingStatus] = []


class OutputsUpdate(StatusUpdate):
    class OutputType(Enum):
        SIREN_LOUD = '0001'
        SIREN_SOFT = '0002'
        SIREN_SOFT_MONITOR = '0004'
        SIREN_SOFT_FIRE = '0008'
        STROBE = '0010'
        RESET = '0020'
        SONALART = '0040'
        KEYPAD_DISPLAY_ENABLE = '0080'
        AUX1 = '0100'
        AUX2 = '0200'
        AUX3 = '0400'
        AUX4 = '0800'
        MONITOR_OUT = '1000'
        POWER_FAIL = '2000'
        PANEL_BATT_FAIL = '4000'
        TAMPER_XPAND = '8000'

    def __init__(self, packet: Packet):
        super(OutputsUpdate, self).__init__(packet)

        self.outputs: List[OutputsUpdate.OutputType] = []


class ViewStateUpdate(StatusUpdate):
    class State(Enum):
        NORMAL = ''
        BRIEF_DAY_CHIME = ''
        HOME = ''
        MEMORY = ''
        BRIEF_DAY_ZONE_SELECT = ''
        EXCLUDE_SELECT = ''
        USER_PROGRAM = ''
        INSTALLER_PROGRAM = ''

    def __init__(self, packet: Packet):
        super(ViewStateUpdate, self).__init__(packet)

        self.states: List[ViewStateUpdate.State] = []
