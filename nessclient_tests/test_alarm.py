from unittest.mock import Mock

import pytest

from nessclient.alarm import Alarm, ArmingState, ArmingMode
from nessclient.event import (
    ArmingUpdate,
    ZoneUpdate_1_16,
    ZoneUpdate_17_32,
    SystemStatusEvent,
)


def test_state_is_initially_unknown(alarm):
    assert alarm.arming_state == ArmingState.UNKNOWN


def test_zones_are_initially_unknown(alarm):
    for zone in alarm.zones:
        assert zone.triggered is None


def test_32_zones_are_created(alarm):
    assert len(alarm.zones) == 32


def test_handle_event_zone_update_1_16(alarm):
    event = ZoneUpdate_1_16(
        included_zones=[ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_1_16.RequestID.ZONE_1_16_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True
    assert alarm.zones[1].triggered is False
    assert alarm.zones[2].triggered is True


def test_handle_event_zone_update_1_16_sealed(alarm):
    alarm.zones[0].triggered = True
    alarm.zones[1].triggered = True

    event = ZoneUpdate_1_16(
        included_zones=[ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_1_16.RequestID.ZONE_1_16_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True
    assert alarm.zones[1].triggered is False
    assert alarm.zones[2].triggered is True


def test_handle_event_zone_update_1_16_callback(alarm):
    for zone in alarm.zones:
        zone.triggered = False
    alarm.zones[3].triggered = True

    cb = Mock()
    alarm.on_zone_change(cb)
    event = ZoneUpdate_1_16(
        included_zones=[ZoneUpdate_1_16.Zone.ZONE_1, ZoneUpdate_1_16.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_1_16.RequestID.ZONE_1_16_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert cb.call_count == 3
    assert cb.call_args_list[0][0] == (1, True)
    assert cb.call_args_list[1][0] == (3, True)
    assert cb.call_args_list[2][0] == (4, False)


def test_handle_event_zone_update_1_16_does_not_affect_17_32(alarm):
    # Seed some 17–32 states
    alarm.zones[16].triggered = True  # zone 17
    alarm.zones[20].triggered = False  # zone 21

    # Apply a 1–16 update
    event = ZoneUpdate_1_16(
        included_zones=[ZoneUpdate_1_16.Zone.ZONE_1],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_1_16.RequestID.ZONE_1_16_INPUT_UNSEALED,
    )
    alarm.handle_event(event)

    # Zones in 17–32 bank unchanged
    assert alarm.zones[16].triggered is True
    assert alarm.zones[20].triggered is False


def test_handle_event_zone_update_17_32(alarm):
    event = ZoneUpdate_17_32(
        included_zones=[
            ZoneUpdate_17_32.Zone.ZONE_17,
            ZoneUpdate_17_32.Zone.ZONE_19,
        ],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_17_32.RequestID.ZONE_17_32_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert alarm.zones[16].triggered is True
    assert alarm.zones[17].triggered is False
    assert alarm.zones[18].triggered is True


def test_handle_event_zone_update_17_32_sealed(alarm):
    alarm.zones[16].triggered = True  # zone 17
    alarm.zones[17].triggered = True  # zone 18

    event = ZoneUpdate_17_32(
        included_zones=[
            ZoneUpdate_17_32.Zone.ZONE_17,
            ZoneUpdate_17_32.Zone.ZONE_19,
        ],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_17_32.RequestID.ZONE_17_32_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert alarm.zones[16].triggered is True
    assert alarm.zones[17].triggered is False
    assert alarm.zones[18].triggered is True


def test_handle_event_zone_update_17_32_callback(alarm):
    # Similar to 1–16 callback test: seed a zone True, others False
    for z in alarm.zones:
        z.triggered = False
    alarm.zones[19].triggered = True  # zone 20

    cb = Mock()
    alarm.on_zone_change(cb)

    event = ZoneUpdate_17_32(
        included_zones=[
            ZoneUpdate_17_32.Zone.ZONE_17,
            ZoneUpdate_17_32.Zone.ZONE_19,
        ],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_17_32.RequestID.ZONE_17_32_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert cb.call_count == 3
    assert cb.call_args_list[0][0] == (17, True)
    assert cb.call_args_list[1][0] == (19, True)
    assert cb.call_args_list[2][0] == (20, False)


def test_handle_event_zone_update_17_32_does_not_affect_1_16(alarm):
    # Seed some 1–16 states
    alarm.zones[0].triggered = True  # zone 1
    alarm.zones[5].triggered = False  # zone 6

    # Apply a 17–32 update
    event = ZoneUpdate_17_32(
        included_zones=[ZoneUpdate_17_32.Zone.ZONE_17],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate_17_32.RequestID.ZONE_17_32_INPUT_UNSEALED,
    )
    alarm.handle_event(event)

    # Zones in 1–16 bank unchanged
    assert alarm.zones[0].triggered is True
    assert alarm.zones[5].triggered is False


def test_handle_event_arming_update_exit_delay(alarm):
    event = ArmingUpdate(
        status=[ArmingUpdate.ArmingStatus.AREA_1_ARMED], address=None, timestamp=None
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.EXIT_DELAY


def test_handle_event_arming_update_fully_armed(alarm):
    event = ArmingUpdate(
        status=[
            ArmingUpdate.ArmingStatus.AREA_1_ARMED,
            ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED,
        ],
        address=None,
        timestamp=None,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ARMED


def test_handle_event_arming_update_disarmed(alarm):
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_infer_arming_state_armed_empty():
    alarm = Alarm(infer_arming_state=True)
    alarm.arming_state = ArmingState.ARMED
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ARMED


def test_handle_event_arming_update_without_infer_arming_state_armed_empty():
    alarm = Alarm(infer_arming_state=False)
    alarm.arming_state = ArmingState.ARMED
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_infer_arming_state_unknown_empty():
    alarm = Alarm(infer_arming_state=True)
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_callback(alarm):
    # emit a SystemStatusEvent for an arming mode to test that it is emitted
    # during EXIT_DELAY state change.
    alarm.handle_event(
        SystemStatusEvent(
            address=None,
            timestamp=None,
            type=SystemStatusEvent.EventType.ARMED_AWAY,
            area=0,
            zone=1,
        )
    )

    cb = Mock()
    alarm.on_state_change(cb)

    event = ArmingUpdate(
        status=[ArmingUpdate.ArmingStatus.AREA_1_ARMED], address=None, timestamp=None
    )
    alarm.handle_event(event)
    assert cb.call_count == 1
    assert cb.call_args[0] == (ArmingState.EXIT_DELAY, ArmingMode.ARMED_AWAY)


def test_handle_event_system_status_unsealed_zone(alarm):
    alarm.zones[0].triggered = False

    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.UNSEALED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True


def test_handle_event_system_status_unsealed_zone_calls_callback(alarm):
    alarm.zones[0].triggered = False

    cb = Mock()
    alarm.on_zone_change(cb)
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.UNSEALED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert cb.call_count == 1
    assert cb.call_args[0] == (1, True)


def test_handle_event_system_status_sealed_zone(alarm):
    alarm.zones[0].triggered = True

    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.SEALED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is False


def test_handle_event_system_status_sealed_zone_calls_callback(alarm):
    alarm.zones[0].triggered = True

    cb = Mock()
    alarm.on_zone_change(cb)
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.SEALED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert cb.call_count == 1
    assert cb.call_args[0] == (1, False)


def test_handle_event_system_status_alarm(alarm):
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ALARM,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.TRIGGERED


def test_handle_event_system_status_alarm_restore_while_disarmed(alarm):
    alarm.arming_state = ArmingState.DISARMED
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ALARM_RESTORE,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_system_status_alarm_restore_while_triggered(alarm):
    alarm.arming_state = ArmingState.TRIGGERED
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ALARM_RESTORE,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ARMED


def test_handle_event_system_status_entry_delay_start(alarm):
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ENTRY_DELAY_START,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ENTRY_DELAY


def test_handle_event_system_status_entry_delay_end(alarm):
    """
    We explicitly ignore entry delay end, since an additional arm event
    is generated, which is handled instead
    """
    alarm.arming_state = ArmingState.ENTRY_DELAY
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ENTRY_DELAY_END,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ENTRY_DELAY


def test_handle_event_system_status_exit_delay_start(alarm):
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.EXIT_DELAY_START,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.EXIT_DELAY


def test_handle_event_system_status_exit_delay_end_from_exit_delay(alarm):
    alarm.arming_state = ArmingState.EXIT_DELAY
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.EXIT_DELAY_END,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ARMED


def test_handle_event_system_status_exit_delay_end_from_armed(alarm):
    alarm.arming_state = ArmingState.DISARMED
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.EXIT_DELAY_END,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_system_status_arm_events(alarm):
    for event_type in Alarm.ARM_EVENTS_MAP.keys():
        alarm.arming_state = ArmingState.DISARMED
        event = SystemStatusEvent(
            address=None, timestamp=None, type=event_type, area=0, zone=1
        )
        assert alarm.arming_state == ArmingState.DISARMED
        alarm.handle_event(event)
        assert alarm.arming_state == ArmingState.ARMING


def test_handle_event_system_status_disarmed(alarm):
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.DISARMED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_system_status_arming_delayed(alarm):
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ARMING_DELAYED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.UNKNOWN


@pytest.fixture
def alarm():
    return Alarm()
