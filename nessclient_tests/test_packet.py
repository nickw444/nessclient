import datetime
import logging
import unittest
from os import path

from nessclient import BaseEvent
from nessclient.packet import Packet, CommandType

_LOGGER = logging.getLogger(__name__)


def fixture_path(fixture_name: str):
    return path.join(path.dirname(__file__), "fixtures", fixture_name)


class PacketTestCase(unittest.TestCase):
    def test_decode_encode_identity(self):
        cases = [
            # '8700036100070018092118370677',
            "8300c6012345678912EE7"
        ]

        for case in cases:
            pkt = Packet.decode(case)
            self.assertEqual(case, pkt.encode())

    def test_decode(self):
        with open(fixture_path("sample_output.txt")) as f:
            for line in f.readlines():
                line = line.strip()
                pkt = Packet.decode(line)
                _LOGGER.info("Decoded '%s' into %s", line, pkt)

    def test_user_interface_packet_decode(self):
        pkt = Packet.decode("8300c6012345678912EE7")
        self.assertEqual(pkt.start, 0x83)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 12)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "12345678912E")
        self.assertIsNone(pkt.timestamp)
        self.assertEqual(pkt.checksum, 0xE7)

    def test_system_status_packet_decode(self):
        pkt = Packet.decode("8700036100070018092118370974")
        self.assertEqual(pkt.start, 0x87)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, "000700")
        self.assertEqual(
            pkt.timestamp,
            datetime.datetime(year=2018, month=9, day=21, hour=18, minute=37, second=9),
        )
        # self.assertEqual(pkt.checksum, 0x74)

    def test_decode_with_address_and_time(self):
        pkt = Packet.decode("8709036101050018122709413536")
        self.assertEqual(pkt.address, 0x09)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, "010500")
        self.assertEqual(
            pkt.timestamp,
            datetime.datetime(year=2018, month=12, day=27, hour=9, minute=41, second=35),
        )
        self.assertFalse(pkt.is_user_interface_resp)

    def test_decode_without_address(self):
        pkt = Packet.decode("820361230001f6")
        self.assertIsNone(pkt.address)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, "230001")
        self.assertIsNone(pkt.timestamp)
        self.assertFalse(pkt.is_user_interface_resp)

    def test_decode_with_address(self):
        pkt = Packet.decode("820003600000001b")
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "000000")
        self.assertIsNone(pkt.timestamp)
        self.assertTrue(pkt.is_user_interface_resp)

    def test_encode_decode1(self):
        pkt = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data="A1234E",
            timestamp=None,
        )
        self.assertEqual(pkt.length, 6)
        self.assertEqual(pkt.encode(), "8300660A1234E49")

    def test_encode_cecode2(self):
        pkt = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data="000100",
            timestamp=datetime.datetime(
                year=2018, month=5, day=10, hour=15, minute=32, second=55
            ),
        )
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.encode(), "87000360000100180510153255E3")

    def test_decode_status_update_response(self):
        """
        82 00 03 60 070000 14
        """
        pkt = Packet.decode("8200036007000014")
        self.assertEqual(pkt.start, 0x82)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "070000")
        self.assertIsNone(pkt.timestamp)
        # self.assertEqual(pkt.checksum, 0x14)

    def test_bad_timestamp(self):
        pkt = Packet.decode("8700036100070019022517600057")
        self.assertEqual(pkt.start, 0x87)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, "000700")
        self.assertEqual(
            pkt.timestamp,
            datetime.datetime(year=2019, month=2, day=25, hour=18, minute=0, second=0),
        )

    def test_decode_zone_16(self):
        pkt = Packet.decode("8700036100160019022823032274")
        self.assertEqual(pkt.start, 0x87)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, "001600")
        self.assertEqual(
            pkt.timestamp,
            datetime.datetime(year=2019, month=2, day=28, hour=23, minute=3, second=22),
        )

    def test_decode_update(self):
        pkt = Packet.decode("820003601700867e")
        event = BaseEvent.decode(pkt)
        print(pkt)
        print(event)

    def test_decode_status_update_response_zone_17_32_none(self):
        # Zone 17-32 Input Unsealed (ID 0x20), no zones set
        pkt = Packet.decode("82000360200000ff")
        self.assertEqual(pkt.start, 0x82)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "200000")
        self.assertIsNone(pkt.timestamp)
        self.assertTrue(pkt.is_user_interface_resp)

    def test_decode_status_update_response_zone_17_32_in_alarm_zone17(self):
        # Zone 17-32 In Alarm (ID 0x25), Zone 17 set
        pkt = Packet.decode("82000360250100aa")
        self.assertEqual(pkt.data, "250100")
        self.assertTrue(pkt.is_user_interface_resp)

    def test_decode_status_update_response_zone_23_unsealed_example(self):
        # From FORM 5 examples in the spec (address 0x07)
        # Example: Zone 23 unseal (ID 0x20, data 0x4000)
        pkt = Packet.decode("8207036020400013")
        self.assertEqual(pkt.start, 0x82)
        self.assertEqual(pkt.address, 0x07)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "204000")
        self.assertTrue(pkt.is_user_interface_resp)

    def test_decode_status_update_response_zone_23_24_unsealed_example(self):
        # From FORM 5 examples in the spec (address 0x07)
        # Example: Zones 23 and 24 unseal (ID 0x20, data 0xC000)
        pkt = Packet.decode("8207036020c00054")
        self.assertEqual(pkt.address, 0x07)
        self.assertEqual(pkt.data, "20c000")
        self.assertTrue(pkt.is_user_interface_resp)
