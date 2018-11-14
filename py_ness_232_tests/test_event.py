import unittest

from py_ness_232.event import ZoneUpdate, pack_unsigned_short_data_enum, ArmingUpdate, BaseEvent, StatusUpdate, \
    ViewStateUpdate
from py_ness_232.packet import Packet


class UtilsTestCase(unittest.TestCase):
    def test_pack_unsigned_short_data_enum(self):
        value = [ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_4]
        self.assertEqual(
            '0900',
            pack_unsigned_short_data_enum(value),
        )


class ArmingUpdateTestCase(unittest.TestCase):
    def test_encode(self):
        event = ArmingUpdate(
            status=[ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED],
            timestamp=None,
            address=0x00)
        pkt = event.encode()
        print(pkt.encode())

        event = BaseEvent.decode(pkt)


class ZoneUpdateTestCase(unittest.TestCase):
    def test_encode(self):
        event = ZoneUpdate(
            included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
            request_id=StatusUpdate.RequestID.ZONE_INPUT_UNSEALED,
            timestamp=None,
            address=0x00)
        pkt = event.encode()
        print(pkt.encode())

        event = BaseEvent.decode(pkt)
        print(event)


class ViewStateUpdateTestCase(unittest.TestCase):
    def test_decode(self):
        pkt = Packet.decode('8200036016f00015')
        event = ViewStateUpdate.decode(pkt)
        self.assertEqual(event.state, ViewStateUpdate.State.NORMAL)
