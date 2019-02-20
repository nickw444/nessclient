import datetime
import logging
import unittest
from os import path

from nessclient.packet import Packet, CommandType

_LOGGER = logging.getLogger(__name__)


def fixture_path(fixture_name: str):
    return path.join(path.dirname(__file__), 'fixtures', fixture_name)


class PacketTestCase(unittest.TestCase):
    def testDecodeEncodeIdentity(self):
        cases = [
            # '8700036100070018092118370677',
            '8300c6012345678912EE7'
        ]

        for case in cases:
            pkt = Packet.decode(case)
            self.assertEqual(case, pkt.encode())

    def testDecode(self):
        with open(fixture_path('sample_output.txt')) as f:
            for line in f.readlines():
                line = line.strip()
                pkt = Packet.decode(line)
                _LOGGER.info("Decoded '%s' into %s", line, pkt)

    def testUserInterfacePacketDecode(self):
        pkt = Packet.decode('8300c6012345678912EE7')
        self.assertEqual(pkt.start, 0x83)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 12)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, '12345678912E')
        self.assertIsNone(pkt.timestamp)
        self.assertEqual(pkt.checksum, 0xe7)

    def testSystemStatusPacketDecode(self):
        pkt = Packet.decode('8700036100070018092118370974')
        self.assertEqual(pkt.start, 0x87)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, '000700')
        self.assertEqual(pkt.timestamp, datetime.datetime(
            year=2018, month=9, day=21, hour=18, minute=37, second=9))
        # self.assertEqual(pkt.checksum, 0x74)

    def testDecodeWithAddressAndTime(self):
        pkt = Packet.decode('8709036101050018122709413536')
        self.assertEqual(pkt.address, 0x09)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, '010500')
        self.assertEqual(pkt.timestamp, datetime.datetime(
            year=2018, month=12, day=27, hour=9, minute=41, second=35))
        self.assertFalse(pkt.is_user_interface_resp)

    def testDecodeWithoutAddress(self):
        pkt = Packet.decode('820361230001f6')
        self.assertIsNone(pkt.address)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.SYSTEM_STATUS)
        self.assertEqual(pkt.data, '230001')
        self.assertIsNone(pkt.timestamp)
        self.assertFalse(pkt.is_user_interface_resp)

    def testDecodeWithAddress(self):
        pkt = Packet.decode('820003600000001b')
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, '000000')
        self.assertIsNone(pkt.timestamp)
        self.assertTrue(pkt.is_user_interface_resp)

    def testEncodeDecode1(self):
        pkt = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data='A1234E',
            timestamp=None,
        )
        self.assertEqual(pkt.length, 6)
        self.assertEqual(pkt.encode(), '8300660A1234E49')

    def testEncodeDecode2(self):
        pkt = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data='000100',
            timestamp=datetime.datetime(
                year=2018, month=5, day=10, hour=15, minute=32, second=55),
        )
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.encode(), '87000360000100180510153255E3')

    def testDecodeStatusUpdateResponse(self):
        '''
        82 00 03 60 070000 14
        '''
        pkt = Packet.decode('8200036007000014')
        self.assertEqual(pkt.start, 0x82)
        self.assertEqual(pkt.address, 0x00)
        self.assertEqual(pkt.length, 3)
        self.assertEqual(pkt.seq, 0x00)
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, '070000')
        self.assertIsNone(pkt.timestamp)
        # self.assertEqual(pkt.checksum, 0x14)
