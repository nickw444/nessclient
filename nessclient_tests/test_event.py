import unittest
from typing import cast

from nessclient.event import (
    ZoneUpdate_1_16,
    ZoneUpdate_17_32,
    pack_unsigned_short_data_enum,
    ArmingUpdate,
    StatusUpdate,
    ViewStateUpdate,
    OutputsUpdate,
    SystemStatusEvent,
    MiscellaneousAlarmsUpdate,
    BaseEvent,
    AuxiliaryOutputsUpdate,
    PanelVersionUpdate,
    DecodeOptions,
)
from nessclient.packet import Packet, CommandType


class UtilsTestCase(unittest.TestCase):
    def test_pack_unsigned_short_data_enum(self):
        value = [ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_4]
        self.assertEqual(
            "0900",
            pack_unsigned_short_data_enum(value),
        )


class BaseEventTestCase(unittest.TestCase):
    def test_decode_system_status_event(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "000000")
        event = BaseEvent.decode(pkt)
        self.assertTrue(isinstance(event, SystemStatusEvent))

    def test_decode_user_interface_event(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "000000")
        event = BaseEvent.decode(pkt)
        self.assertTrue(isinstance(event, StatusUpdate))

    def test_decode_unknown_event(self):
        pkt = make_packet(cast(CommandType, 0x01), "000000")
        self.assertRaises(ValueError, lambda: BaseEvent.decode(pkt))


class StatusUpdateTestCase(unittest.TestCase):
    def test_decode_zone_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "000000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ZoneUpdate_1_16))

    def test_decode_zone_17_32_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "200000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ZoneUpdate_17_32))

    def test_decode_misc_alarms_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "130000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, MiscellaneousAlarmsUpdate))

    def test_decode_arming_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "140000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ArmingUpdate))

    def test_decode_outputs_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "150000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, OutputsUpdate))

    def test_decode_view_state_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "16f000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, ViewStateUpdate))

    def test_decode_panel_version_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, PanelVersionUpdate))

    def test_decode_auxiliary_outputs_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "180000")
        event = StatusUpdate.decode(pkt)
        self.assertTrue(isinstance(event, AuxiliaryOutputsUpdate))

    def test_decode_unknown_update(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "550000")
        self.assertRaises(ValueError, lambda: StatusUpdate.decode(pkt))


class ArmingUpdateTestCase(unittest.TestCase):
    def test_encode(self):
        event = ArmingUpdate(
            status=[ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED],
            timestamp=None,
            address=0x00,
        )
        pkt = event.encode()
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "140400")
        self.assertTrue(pkt.is_user_interface_resp)

    def test_area1_armed(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "140500")
        event = ArmingUpdate.decode(pkt)
        self.assertEqual(
            event.status,
            [
                ArmingUpdate.ArmingStatus.AREA_1_ARMED,
                ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED,
            ],
        )


class ZoneUpdate1To16TestCase(unittest.TestCase):
    def test_encode(self):
        event = ZoneUpdate_1_16(
            included_zones=[ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_3],
            request_id=StatusUpdate.RequestID.ZONE_1_16_INPUT_UNSEALED,
            timestamp=None,
            address=0x00,
        )
        pkt = event.encode()
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "000500")
        self.assertTrue(pkt.is_user_interface_resp)

    def test_zone_in_delay_no_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "030000")
        event = ZoneUpdate_1_16.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate_1_16.RequestID.ZONE_1_16_IN_DELAY)
        self.assertEqual(event.included_zones, [])

    def test_zone_in_delay_with_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "030500")
        event = ZoneUpdate_1_16.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate_1_16.RequestID.ZONE_1_16_IN_DELAY)
        self.assertEqual(
            event.included_zones,
            [ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_3],
        )

    def test_zone_in_alarm_with_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "051400")
        event = ZoneUpdate_1_16.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate_1_16.RequestID.ZONE_1_16_IN_ALARM)
        self.assertEqual(
            event.included_zones,
            [ZoneUpdate_1_16.Zone.ZONE_3, ZoneUpdate_1_16.Zone.ZONE_5],
        )

    def test_zone_1_16_excluded_plus_auto(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "190500")
        event = ZoneUpdate_1_16.decode(pkt)
        self.assertEqual(
            event.request_id,
            ZoneUpdate_1_16.RequestID.ZONE_1_16_EXCLUDED_PLUS_AUTO_EXCLUDED,
        )
        self.assertEqual(
            event.included_zones,
            [ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_3],
        )


class ZoneUpdate17To32TestCase(unittest.TestCase):
    def test_encode(self):
        event = ZoneUpdate_17_32(
            included_zones=[
                ZoneUpdate_17_32.Zone.ZONE_17,
                ZoneUpdate_17_32.Zone.ZONE_19,
            ],
            request_id=StatusUpdate.RequestID.ZONE_17_32_INPUT_UNSEALED,
            timestamp=None,
            address=0x00,
        )
        pkt = event.encode()
        self.assertEqual(pkt.command, CommandType.USER_INTERFACE)
        self.assertEqual(pkt.data, "200500")
        self.assertTrue(pkt.is_user_interface_resp)

    def test_zone_in_delay_no_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "230000")
        event = ZoneUpdate_17_32.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate_17_32.RequestID.ZONE_17_32_IN_DELAY)
        self.assertEqual(event.included_zones, [])

    def test_zone_in_delay_with_zones(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "230500")
        event = ZoneUpdate_17_32.decode(pkt)
        self.assertEqual(event.request_id, ZoneUpdate_17_32.RequestID.ZONE_17_32_IN_DELAY)
        self.assertEqual(
            event.included_zones,
            [ZoneUpdate_17_32.Zone.ZONE_17, ZoneUpdate_17_32.Zone.ZONE_19],
        )

    def test_zone_excluded_plus_auto(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "330500")
        event = ZoneUpdate_17_32.decode(pkt)
        self.assertEqual(
            event.request_id,
            ZoneUpdate_17_32.RequestID.ZONE_17_32_EXCLUDED_PLUS_AUTO_EXCLUDED,
        )
        self.assertEqual(
            event.included_zones,
            [ZoneUpdate_17_32.Zone.ZONE_17, ZoneUpdate_17_32.Zone.ZONE_19],
        )


class ViewStateUpdateTestCase(unittest.TestCase):
    def test_normal_state(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "16f000")
        event = ViewStateUpdate.decode(pkt)
        self.assertEqual(event.state, ViewStateUpdate.State.NORMAL)


class OutputsUpdateTestCase(unittest.TestCase):
    def test_panic_outputs(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "157100")
        event = OutputsUpdate.decode(pkt)
        self.assertEqual(
            event.outputs,
            [
                OutputsUpdate.OutputType.SIREN_LOUD,
                OutputsUpdate.OutputType.STROBE,
                OutputsUpdate.OutputType.RESET,
                OutputsUpdate.OutputType.SONALART,
            ],
        )


class MiscellaneousAlarmsUpdateTestCase(unittest.TestCase):
    def test_misc_alarms_install_end(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "131000")
        event = MiscellaneousAlarmsUpdate.decode(pkt)
        self.assertEqual(
            event.included_alarms, [MiscellaneousAlarmsUpdate.AlarmType.INSTALL_END]
        )

    def test_misc_alarms_panic(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "130200")
        event = MiscellaneousAlarmsUpdate.decode(pkt)
        self.assertEqual(
            event.included_alarms, [MiscellaneousAlarmsUpdate.AlarmType.PANIC]
        )

    def test_misc_alarms_multi(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "131500")
        event = MiscellaneousAlarmsUpdate.decode(pkt)
        self.assertEqual(
            event.included_alarms,
            [
                MiscellaneousAlarmsUpdate.AlarmType.DURESS,
                MiscellaneousAlarmsUpdate.AlarmType.MEDICAL,
                MiscellaneousAlarmsUpdate.AlarmType.INSTALL_END,
            ],
        )


class SystemStatusEventTestCase(unittest.TestCase):
    def test_exit_delay_end(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "230001")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.EXIT_DELAY_END)

    def test_zone_sealed_with_zone_5(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "010500")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.SEALED)

    def test_zone_unsealed_with_zone_15(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "001500")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 15)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)

    def test_zone_unsealed_with_zone_16(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "001600")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 16)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)

    def test_zone_sealed_with_zone_17_in_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "011701")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 17)
        self.assertEqual(event.type, SystemStatusEvent.EventType.SEALED)

    def test_zone_unsealed_with_zone_17_in_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "001701")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 17)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)

    def test_zone_sealed_with_zone_17(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "011700")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 17)
        self.assertEqual(event.type, SystemStatusEvent.EventType.SEALED)

    def test_zone_unsealed_with_zone_17(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "001700")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 17)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)

    def test_zone_sealed_with_zone_32(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "013200")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 32)
        self.assertEqual(event.type, SystemStatusEvent.EventType.SEALED)

    def test_zone_unsealed_with_zone_32(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "003200")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 32)
        self.assertEqual(event.type, SystemStatusEvent.EventType.UNSEALED)

    def test_zone_alarm_with_zone_5_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "020501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ALARM)

    def test_tamper_unsealed_with_zone_5_radio(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "080591")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0x91)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.TAMPER_UNSEALED)

    def test_power_failure(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "100000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.POWER_FAILURE)

    def test_entry_delay_start(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "200501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ENTRY_DELAY_START)

    def test_output_on(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "310100")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 1)
        self.assertEqual(event.type, SystemStatusEvent.EventType.OUTPUT_ON)

    def test_alarm_restore_with_zone_5_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "030501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ALARM_RESTORE)

    def test_tamper_normal_with_zone_5_radio(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "090591")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0x91)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.TAMPER_NORMAL)

    def test_power_normal(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "110000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.POWER_NORMAL)

    def test_battery_failure(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "120000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.BATTERY_FAILURE)

    def test_battery_normal(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "130000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.BATTERY_NORMAL)

    def test_report_failure(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "140000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.REPORT_FAILURE)

    def test_report_normal(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "150000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.REPORT_NORMAL)

    def test_supervision_failure_zone_5(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "160500")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.SUPERVISION_FAILURE)

    def test_supervision_normal_zone_5(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "170500")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.SUPERVISION_NORMAL)

    def test_real_time_clock(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "190000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.REAL_TIME_CLOCK)

    def test_entry_delay_end(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "210501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ENTRY_DELAY_END)

    def test_exit_delay_start(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "220501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.EXIT_DELAY_START)

    def test_armed_away(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "240101")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 1)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMED_AWAY)

    def test_disarmed(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "2f0101")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 1)
        self.assertEqual(event.type, SystemStatusEvent.EventType.DISARMED)

    def test_arming_delayed(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "300101")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 1)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMING_DELAYED)

    def test_output_off(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "320100")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 1)
        self.assertEqual(event.type, SystemStatusEvent.EventType.OUTPUT_OFF)

    def test_manual_exclude_with_zone_5_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "040501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.MANUAL_EXCLUDE)

    def test_manual_include_with_zone_5_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "050501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.MANUAL_INCLUDE)

    def test_auto_exclude_with_zone_5_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "060501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.AUTO_EXCLUDE)

    def test_auto_include_with_zone_5_area_1(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "070501")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 1)
        self.assertEqual(event.zone, 5)
        self.assertEqual(event.type, SystemStatusEvent.EventType.AUTO_INCLUDE)

    def test_armed_home(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "250103")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 3)
        self.assertEqual(event.zone, 1)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMED_HOME)

    def test_armed_day(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "260004")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 4)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMED_DAY)

    def test_armed_night(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "270000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMED_NIGHT)

    def test_armed_vacation(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "280000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMED_VACATION)

    def test_armed_highest(self):
        pkt = make_packet(CommandType.SYSTEM_STATUS, "2e0000")
        event = SystemStatusEvent.decode(pkt)
        self.assertEqual(event.area, 0)
        self.assertEqual(event.zone, 0)
        self.assertEqual(event.type, SystemStatusEvent.EventType.ARMED_HIGHEST)


Rev16DecodeOptions = DecodeOptions(
    panel_version_update_model_mapper=PanelVersionUpdate.ModelRev16Mapper
)
LegacyDecodeOptions = DecodeOptions(
    panel_version_update_model_mapper=PanelVersionUpdate.ModelLegacyMapper
)


class PanelVersionUpdateTestCase(unittest.TestCase):
    def test_inferred_d16x_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170000")
        event = PanelVersionUpdate.decode(pkt)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X)

    def test_inferred_d16x_cel_4g_model_via_fallback(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "171500")
        event = PanelVersionUpdate.decode(pkt)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X_CEL_4G)

    def test_rev16_d8x_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170000")
        event = PanelVersionUpdate.decode(pkt, Rev16DecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D8X)

    def test_rev16_d8xcel_3g_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170400")
        event = PanelVersionUpdate.decode(pkt, Rev16DecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D8X_CEL_3G)

    def test_rev16_d16x_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "171000")
        event = PanelVersionUpdate.decode(pkt, Rev16DecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X)

    def test_rev16_d16xcel_3g_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "171400")
        event = PanelVersionUpdate.decode(pkt, Rev16DecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X_CEL_3G)

    def test_rev16_d16xcel_4g_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "171500")
        event = PanelVersionUpdate.decode(pkt, Rev16DecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X_CEL_4G)

    def test_legacy_d16x_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170000")
        event = PanelVersionUpdate.decode(pkt, LegacyDecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X)

    def test_legacy_d16x_cel_3g_model_1(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170400")
        event = PanelVersionUpdate.decode(pkt, LegacyDecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X_CEL_3G)

    def test_legacy_d16x_cel_3g_model_2(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "171400")
        event = PanelVersionUpdate.decode(pkt, LegacyDecodeOptions)
        self.assertEqual(event.model, PanelVersionUpdate.Model.D16X_CEL_3G)

    def test_legacy_unhandled_model(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "171300")
        self.assertRaises(
            KeyError, lambda: PanelVersionUpdate.decode(pkt, LegacyDecodeOptions)
        )

    def test_sw_version(self):
        cases = [
            ("170078", 7, 8, "7.8"),
            ("170080", 8, 0, "8.0"),
            ("1714a8", 10, 8, "10.8"),
            ("170086", 8, 6, "8.6"),
            ("170087", 8, 7, "8.7"),
            ("1715b0", 11, 0, "11.0"),
        ]
        for data, major, minor, version in cases:
            with self.subTest(data=data):
                pkt = make_packet(CommandType.USER_INTERFACE, data)
                event = PanelVersionUpdate.decode(pkt)
                self.assertEqual(event.major_version, major)
                self.assertEqual(event.minor_version, minor)
                self.assertEqual(event.version, version)


class AuxiliaryOutputsUpdateTestCase(unittest.TestCase):
    def test_aux_output_1(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170001")
        event = AuxiliaryOutputsUpdate.decode(pkt)
        self.assertEqual(
            event.outputs,
            [
                AuxiliaryOutputsUpdate.OutputType.AUX_1,
            ],
        )

    def test_aux_output_4(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170008")
        event = AuxiliaryOutputsUpdate.decode(pkt)
        self.assertEqual(
            event.outputs,
            [
                AuxiliaryOutputsUpdate.OutputType.AUX_4,
            ],
        )

    def test_aux_output_multi(self):
        pkt = make_packet(CommandType.USER_INTERFACE, "170088")
        event = AuxiliaryOutputsUpdate.decode(pkt)
        self.assertEqual(
            event.outputs,
            [
                AuxiliaryOutputsUpdate.OutputType.AUX_4,
                AuxiliaryOutputsUpdate.OutputType.AUX_8,
            ],
        )


def make_packet(command: CommandType, data: str):
    return Packet(
        address=0,
        command=command,
        seq=0,
        timestamp=None,
        data=data,
        is_user_interface_resp=True,
    )
