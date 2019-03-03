import unittest
from typing import cast

from nessclient.event import (
    ZoneUpdate, pack_unsigned_short_data_enum, ArmingUpdate,
    StatusUpdate, ViewStateUpdate, OutputsUpdate, SystemStatusEvent,
    MiscellaneousAlarmsUpdate, BaseEvent)
from nessclient.packet import Packet, CommandType


class UtilsTestCase(unittest.TestCase):
    def test_pack_unsigned_short_data_enum(self):
        value = [ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_4]
        self.assertEqual(
            '0900',
            pack_unsigned_short_data_enum(value),
        )


class BaseEventTestCase(unittest.TestCase):
    def test_decode_system_status_event(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, '000000')
        event = BaseEvent.decode(pkt)
        self.assertTrue(isinstance(event, SystemStatusEvent))

    def test_decode_user_interface_event(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '000000')
        event = BaseEvent.decode(pkt)
        self.assertTrue(isinstance(event, StatusUpdate))

    def test_decode_unknown_event(self):
        pkt = make_packet(cast(CommandType, 0x01), '000000')
        self.assertRaises(ValueError, lambda: BaseEvent.decode(pkt))


class StatusUpdateTestCase(unittest.TestCase):
    def test_decode_zone_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '000000')
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ZoneUpdate))

    def test_decode_misc_alarms_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '130000')
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, MiscellaneousAlarmsUpdate))

    def test_decode_arming_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '140000')
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ArmingUpdate))

    def test_decode_outputs_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '150000')
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, OutputsUpdate))

    def test_decode_view_state_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '16f000')
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ViewStateUpdate))

    def test_decode_unknown_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '550000')
        self.assertRaises(ValueError, lambda: StatusUpdate.decode(pkt))


class ArmingUpdateTestCase(unittest.TestCase):
    def test_encode(self):
        event = ArmingUpdate(
            status=[ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED],
            timestamp=None,
            address=0x00)
        pkt = event.encode()
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, '140400')
        self.assertTrue(pkt.is_user_interface_resp)

    def test_area1_armed(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '140500')
        event = ArmingUpdate.decode(pkt)
        self.assertEqual(event.status, [
            ArmingUpdate.ArmingStatus.AREA_1_ARMED,
            ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED
        ])


class ZoneUpdateTestCase(unittest.TestCase):
    def test_encode(self):
        event = ZoneUpdate(
            included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
            request_id=StatusUpdate.RequestID.ZONE_INPUT_UNSEALED,
            timestamp=None,
            address=0x00)
        pkt = event.encode()
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, '000500')
        self.assertTrue(pkt.is_user_interface_resp)

    def test_zone_in_delay_no_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '030000')
        event = ZoneUpdate.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate.RequestID.ZONE_IN_DELAY)
        self.assertEqual(event.included_zones, [])

    def test_zone_in_delay_with_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '030500')
        event = ZoneUpdate.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate.RequestID.ZONE_IN_DELAY)
        self.assertEqual(event.included_zones,
                         [ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3])

    def test_zone_in_alarm_with_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '051400')
        event = ZoneUpdate.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate.RequestID.ZONE_IN_ALARM)
        self.assertEqual(event.included_zones,
                         [ZoneUpdate.Zone.ZONE_3, ZoneUpdate.Zone.ZONE_5])


class ViewStateUpdateTestCase(unittest.TestCase):
    def test_normal_state(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '16f000')
        event = ViewStateUpdate.decode(pkt)
        self.assertEqual(event.state, ViewStateUpdate.State.NORMAL)


class OutputsUpdateTestCase(unittest.TestCase):
    def test_panic_outputs(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '157100')
        event = OutputsUpdate.decode(pkt)
        self.assertEqual(event.outputs, [
            OutputsUpdate.OutputType.SIREN_LOUD,
            OutputsUpdate.OutputType.STROBE,
            OutputsUpdate.OutputType.RESET,
            OutputsUpdate.OutputType.SONALART
        ])


class MiscellaneousAlarmsUpdateTestCase(unittest.TestCase):
    def test_misc_alarms_install_end(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '131000')
        event = MiscellaneousAlarmsUpdate.decode(pkt)
        self.assertEqual(event.included_alarms,
                         [MiscellaneousAlarmsUpdate.AlarmType.INSTALL_END])

    def test_misc_alarms_panic(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '130200')
        event = MiscellaneousAlarmsUpdate.decode(pkt)
        self.assertEqual(event.included_alarms,
                         [MiscellaneousAlarmsUpdate.AlarmType.PANIC])

    def test_misc_alarms_multi(self):
        pkt = make_packet(CommandType.USER_INTERFACE, '131500')
        event = MiscellaneousAlarmsUpdate.decode(pkt)
        self.assertEqual(event.included_alarms,
                         [MiscellaneousAlarmsUpdate.AlarmType.DURESS,
                          MiscellaneousAlarmsUpdate.AlarmType.MEDICAL,
                          MiscellaneousAlarmsUpdate.AlarmType.INSTALL_END])


class SystemStatusEventTestCase(unittest.TestCase):
    def test_exit_delay_end(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, '230001')
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type,
                         SystemStatusEvent.EventType.EXIT_DELAY_END)

    def test_zone_sealed(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, '010500')
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type,
                         SystemStatusEvent.EventType.SEALED)

    def test_zone_unsealed_with_zone_15(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, '001500')
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 15)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)

    def test_zone_unsealed_with_zone_16(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, '001600')
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 16)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)


def make_packet(command: CommandType, data: str):
    return Packet(address=0, command=command,
                  seq=0, timestamp=None, data=data,
                  is_user_interface_resp=True)
