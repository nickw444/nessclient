import datetime
import logging
import unittest
import pytest
from os import path

from nessclient import BaseEvent
from nessclient.event import SystemStatusEvent, StatusUpdate
from nessclient.packet import Packet, CommandType
from nessclient_tests.fixtures.real_captured_test_data import (
    Output_From_Ness_Event_Data_Real_Packets,
    Output_From_Ness_Status_Update_Real_Packets,
)
from nessclient_tests.fixtures.generate_test_packets import (
    gemerate_input_to_ness_user_interface_valid_packets,
    gemerate_output_from_ness_event_data_valid_packets,
    gemerate_output_from_ness_status_update_valid_packets,
)

_LOGGER = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(threadName)-25s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def fixture_path(fixture_name: str) -> str:
    return path.join(path.dirname(__file__), "fixtures", fixture_name)


class PacketTestCase(unittest.TestCase):
    @pytest.mark.skip(reason="Calculates wrong checksum")
    def test_decode_encode_identity(self) -> None:
        cases = ["8300C6012345678912E07"]

        for case in cases:
            pkt = Packet.decode(case)
            assert case == pkt.encode()

    def test_decode1(self) -> None:
        with open(fixture_path("sample_output.txt")) as f:
            for line in f.readlines():
                line = line.strip() + ""
                pkt = Packet.decode(line)
                _LOGGER.info("Decoded '%s' into %s", line, pkt)

    def test_user_interface_packet_decode(self):
        pkt = Packet.decode("8300c6012345678912EE7")
        assert pkt.start == 0x83
        assert pkt.address == 0x00
        assert pkt.length == 12
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.USER_INTERFACE
        assert pkt.data == "12345678912E"
        assert pkt.timestamp is None
        assert pkt.checksum == 0xE7

    # Bad Input (to Ness) User-Interface Packets
    @pytest.mark.skip(reason="Fails to reject invalid size data")
    def test_create_bad_input_ui_packet_zero_length(self) -> None:
        # Zero Length
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid size data")
    def test_create_bad_input_ui_packet_too_long(self) -> None:
        # Too Long (37 chars)
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid character")
    def test_create_bad_input_ui_packet_invalid_char1(self) -> None:
        # Has a disallowed 'B' character
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="B2345678912E",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid character")
    def test_create_bad_input_ui_packet_invalid_char2(self) -> None:
        # Has a disallowed '\xAA' character
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="\xaa2345678912E",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject - address is required but not supplied")
    def test_create_bad_input_ui_packet_no_address(self) -> None:
        # Has address = None
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=None,
                command=CommandType.USER_INTERFACE,
                data="12345678912E",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject - timestamp is supplied but not allowed")
    def test_create_bad_input_ui_packet_unallowed_timestamp(self) -> None:
        # Has a Timestamp (not allowed)
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                timestamp=datetime.datetime(
                    year=2018, month=9, day=21, hour=18, minute=37, second=9
                ),
                data="12345678912E",
                seq=0,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject - seqence is supplied but not allowed")
    def test_create_bad_input_ui_packet_seqence_invalid(self) -> None:
        # Has a non-zero sequence
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="12345678912E",
                seq=1,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid address")
    def test_create_bad_input_ui_packet_invalid_address(self) -> None:
        # Address too large
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=30,
                command=CommandType.USER_INTERFACE,
                data="12345678912E",
                seq=0,
                timestamp=None,
            ),
        )

    # Bad Output (from Ness) Status Update Packets
    # (Response to a User-Interface Status Request Packet)
    @pytest.mark.skip(reason="Fails to reject invalid length data")
    def test_create_bad_output_update_packet_wrong_length(self) -> None:
        # Wrong length (!=6)
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="0000000000",
                is_user_interface_resp=True,
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid char in data")
    def test_create_bad_output_update_packet_invalid_char(self) -> None:
        # Non-Hex character 'X'
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="X00000",
                is_user_interface_resp=True,
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject when expected address is None")
    def test_create_bad_output_update_packet_no_address(self) -> None:
        # Has address = None
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=None,
                command=CommandType.USER_INTERFACE,
                data="000000",
                is_user_interface_resp=True,
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject when timestamp is supplied but unallowed")
    def test_create_bad_output_update_packet_has_timestamp(self) -> None:
        # Has a Timestamp (not allowed)
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                timestamp=datetime.datetime(
                    year=2018, month=9, day=21, hour=18, minute=37, second=9
                ),
                data="000000",
                is_user_interface_resp=True,
                seq=0,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject when sequence is non-zero - unallowed")
    def test_create_bad_output_update_packet_has_sequence(self) -> None:
        # Has a non-zero sequence
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="000000",
                is_user_interface_resp=True,
                seq=1,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject when address is too large")
    def test_create_bad_output_update_packet_address_too_big(self) -> None:
        # Address too large
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=30,
                command=CommandType.USER_INTERFACE,
                data="000000",
                is_user_interface_resp=True,
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject when unallowed delay marker specified")
    def test_create_bad_output_update_packet_has_delay_marker(self) -> None:
        # Has dis-allowed delay marker
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.USER_INTERFACE,
                data="000000",
                is_user_interface_resp=True,
                has_delay_marker=True,
                seq=0,
                timestamp=None,
            ),
        )

    # Bad Output (from Ness) Event Data Packets

    @pytest.mark.skip(reason="Fails to reject when length is invalid")
    def test_create_bad_output_event_packet_invalid_length(self) -> None:
        # Wrong length (!=6)
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.SYSTEM_STATUS,
                data="0000000000",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid char")
    def test_create_bad_output_event_packet_invalid_char(self) -> None:
        # Non-Hex character 'X'
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.SYSTEM_STATUS,
                data="X00000",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject invalid address")
    def test_create_bad_output_event_packet_invalid_address(self) -> None:
        # Address too large
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=30,
                command=CommandType.SYSTEM_STATUS,
                data="000000",
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Fails to reject unexpected delay marker")
    def test_create_bad_output_event_packet_has_delay_marker(self) -> None:
        # Has dis-allowed delay marker
        self.assertRaises(
            ValueError,
            lambda: Packet(
                address=0,
                command=CommandType.SYSTEM_STATUS,
                data="000000",
                has_delay_marker=True,
                seq=0,
                timestamp=None,
            ),
        )

    @pytest.mark.skip(reason="Some of these are not rejected")
    def test_decode_bad_packets(self) -> None:
        cases = [
            # UI request packets
            "8300c60",  # short packet truncated
            "8300f6012345678912EE4",  # length too long for data
            "830056012345678912E15",  # length too short for data
            "8300c6012345678912EX7",  # Non Hex character in checksum
            "8300c6012345678912EE8",  # Bad checksum (should be E7)
            "8300c6012345678912Ee7",  # Bad checksum (must be upper case)
            "8300c60B2345678912E42A",  # Has a disallowed 'B' character
            "8300c60\xaa2345678912E92",  # Has a disallowed '\xAA' character
            "83000609F",  # Zero length
            "8302560AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA33",  # 37 length  (too long)
            # Bad Output (from Ness) Status Update Packets
            # Bad checksum
            "820003600000001a",
            # Wrong length (!=6)
            "82000460000000001a",
            # Non-Hex character 'X'
            # checksum is also wrong, since it can't be calculated here
            "82000360X000001b",
            # Has a Timestamp (not allowed)
            "82000360000000061201074300b8",
            # Has a non-zero sequence
            "820083600000009b",
            # Address too large
            "8215036000000006",
            # Has dis-allowed delay marker
            "820003600000001b?",
            # Bad Output (from Ness) Event Data Packets
            # Bad checksum
            "8204610000000018"
            "830004610000000017"
            "860461000000180921183709007a"
            "870004610000001809211837090079"
            # Wrong length (!=6)
            "8204610000000019"
            "830004610000000018"
            "860461000000180921183709007b"
            "87000461000000180921183709007a"
            # Non-Hex character 'X'
            # checksum is also wrong, since it can't be calculated here
            "820361X000001a"
            "83000361X0000019"
            "860361X000001809211837097c"
            "87000361X000001809211837097b"
            # Address too large
            "8315036100000004"
            "8715036100000018092118370966"
            # Has dis-allowed delay marker
            "8203610000001a?"
            "8300036100000019?"
            "8603610000001809211837097c?"
            "870003610000001809211837097b?",
        ]

        for case in cases:
            self.assertRaises(ValueError, lambda: Packet.decode(case))

    def test_system_status_packet_decode(self) -> None:
        pkt = Packet.decode("8700036100070018092118370974")
        assert pkt.start == 0x87
        assert pkt.address == 0x00
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.SYSTEM_STATUS
        assert pkt.data == "000700"
        assert pkt.timestamp == datetime.datetime(
            year=2018, month=9, day=21, hour=18, minute=37, second=9
        )
        # assert pkt.checksum == 0x74

    def test_decode_with_address_and_time(self) -> None:
        pkt = Packet.decode("8709036101050018122709413536")
        assert pkt.address == 0x09
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.SYSTEM_STATUS
        assert pkt.data == "010500"
        assert pkt.timestamp == datetime.datetime(
            year=2018, month=12, day=27, hour=9, minute=41, second=35
        )
        assert not pkt.is_user_interface_resp

    def test_decode_without_address(self) -> None:
        pkt = Packet.decode("820361230001f6")
        assert pkt.address is None
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.SYSTEM_STATUS
        assert pkt.data == "230001"
        assert pkt.timestamp is None
        assert not pkt.is_user_interface_resp

    def test_decode_with_address(self) -> None:
        pkt = Packet.decode("820003600000001b")
        assert pkt.address == 0x00
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.USER_INTERFACE
        assert pkt.data == "000000"
        assert pkt.timestamp is None
        assert pkt.is_user_interface_resp

    def test_encode_decode1(self) -> None:
        pkt = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data="A1234E",
            timestamp=None,
        )
        assert pkt.length == 6
        assert pkt.encode() == "8300660A1234E49"

    def test_encode_cecode2(self) -> None:
        pkt = Packet(
            address=0x00,
            seq=0x00,
            command=CommandType.USER_INTERFACE,
            data="000100",
            timestamp=None,
        )
        assert pkt.length == 6
        assert pkt.encode() == "830066000010078"
        assert Packet.decode(pkt.encode()) == pkt

    def test_decode_status_update_response(self) -> None:
        """
        82 00 03 60 070000 14
        """
        pkt = Packet.decode("8200036007000014")
        assert pkt.start == 0x82
        assert pkt.address == 0x00
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.USER_INTERFACE
        assert pkt.data == "070000"
        assert pkt.timestamp is None
        # assert pkt.checksum == 0x14

    def test_bad_timestamp(self) -> None:
        pkt = Packet.decode("8700036100070019022517600057")
        assert pkt.start == 0x87
        assert pkt.address == 0x00
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.SYSTEM_STATUS
        assert pkt.data == "000700"
        assert pkt.timestamp == datetime.datetime(
            year=2019, month=2, day=25, hour=18, minute=0, second=0
        )

    def test_decode_zone_16(self) -> None:
        pkt = Packet.decode("8700036100160019022823032274")
        assert pkt.start == 0x87
        assert pkt.address == 0x00
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.SYSTEM_STATUS
        assert pkt.data == "001600"
        assert pkt.timestamp == datetime.datetime(
            year=2019, month=2, day=28, hour=23, minute=3, second=22
        )

    def test_decode_update(self) -> None:
        pkt = Packet.decode("820003601700867e")
        event = BaseEvent.decode(pkt)
        print(pkt)
        print(event)

    def test_decode_status_update_response_zone_17_32_none(self):
        # Zone 17-32 Input Unsealed (ID 0x20), no zones set
        pkt = Packet.decode("82000360200000ff")
        assert pkt.start == 0x82
        assert pkt.address == 0x00
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.USER_INTERFACE
        assert pkt.data == "200000"
        assert pkt.timestamp is None
        assert pkt.is_user_interface_resp

    def test_decode_status_update_response_zone_17_32_in_alarm_zone17(self):
        # Zone 17-32 In Alarm (ID 0x25), Zone 17 set
        pkt = Packet.decode("82000360250100aa")
        assert pkt.data == "250100"
        assert pkt.is_user_interface_resp

    def test_decode_status_update_response_zone_23_unsealed_example(self):
        # From FORM 5 examples in the spec (address 0x07)
        # Example: Zone 23 unseal (ID 0x20, data 0x4000)
        pkt = Packet.decode("8207036020400013")
        assert pkt.start == 0x82
        assert pkt.address == 0x07
        assert pkt.length == 3
        assert pkt.seq == 0x00
        assert pkt.command == CommandType.USER_INTERFACE
        assert pkt.data == "204000"
        assert pkt.is_user_interface_resp

    def test_decode_status_update_response_zone_23_24_unsealed_example(self):
        # From FORM 5 examples in the spec (address 0x07)
        # Example: Zones 23 and 24 unseal (ID 0x20, data 0xC000)
        pkt = Packet.decode("8207036020c00054")
        assert pkt.address == 0x07
        assert pkt.data == "20c000"
        assert pkt.is_user_interface_resp


class PacketTestRealPackets(unittest.TestCase):
    """Test decoding and re-encoding real captured packets."""

    @pytest.mark.skip(reason="Calculates wrong checksum")
    def test_decode_encode_real_event_packets(self) -> None:
        """Test decoding and re-encoding the real Event packets."""
        for pktdata in Output_From_Ness_Event_Data_Real_Packets:
            pkt = Packet.decode(pktdata)
            event = BaseEvent.decode(pkt)
            assert isinstance(event, SystemStatusEvent)
            assert event.encode().encode() == pktdata

    @pytest.mark.skip(reason="Calculates wrong checksum")
    def test_decode_encode_real_status_packets(self) -> None:
        """Test decoding and re-encoding the real Status Update packets."""
        for pktdata in Output_From_Ness_Status_Update_Real_Packets:
            pkt = Packet.decode(pktdata)
            event = BaseEvent.decode(pkt)
            assert isinstance(event, StatusUpdate)
            assert event.encode().encode() == pktdata


class PacketTestGeneratedPackets(unittest.TestCase):
    """Test decoding and re-encoding all packet types."""

    @pytest.mark.skip(reason="Uses lowercase and Calculates wrong checksum")
    def test_decode_encode_generated_ui_input_packets(self) -> None:
        """Test decoding and re-encoding UI request packets."""
        for test_item in gemerate_input_to_ness_user_interface_valid_packets():
            pkt = Packet.decode(test_item.packet_chars)
            assert pkt.encode() == test_item.packet_chars

    @pytest.mark.skip(reason="Calculates wrong checksum")
    def test_decode_encode_generated_ui_response_packets(self) -> None:
        """Test decoding and re-encoding Status Update Responses."""
        for test_pkt in gemerate_output_from_ness_status_update_valid_packets():
            pkt = Packet.decode(test_pkt.packet_chars)
            event = BaseEvent.decode(pkt)
            assert isinstance(event, StatusUpdate)
            assert pkt.encode() == test_pkt.packet_chars

    @pytest.mark.skip(reason="Uses lowercase and Calculates wrong checksum")
    def test_decode_encode_generated_status_packets(self) -> None:
        """Test decoding and re-encoding System Status Output Events."""
        for test_pkt in gemerate_output_from_ness_event_data_valid_packets():
            pkt = Packet.decode(test_pkt.packet_chars)
            event = BaseEvent.decode(pkt)
            assert isinstance(event, SystemStatusEvent)
            assert event.encode().encode() == test_pkt.packet_chars
