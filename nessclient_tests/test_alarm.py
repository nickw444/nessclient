"""Test the state machines in the nessclient.Alarm class."""

from unittest.mock import Mock

import pytest

from nessclient.alarm import Alarm, ArmingState, ArmingMode
from nessclient.event import ArmingUpdate, ZoneUpdate, SystemStatusEvent


def test_state_is_initially_unknown(alarm: Alarm) -> None:
    """Check that the arming state starts as Unknown."""
    assert alarm.arming_state == ArmingState.UNKNOWN


def test_zones_are_initially_unknown(alarm: Alarm) -> None:
    """Check that the zone states start as Unknown."""
    for zone in alarm.zones:
        assert zone.triggered is None


def test_16_zones_are_created(alarm: Alarm) -> None:
    """Check that the expected number of zones are created."""
    assert len(alarm.zones) == 16


def test_handle_event_zone_update(alarm: Alarm) -> None:
    """Check that ZoneUpdate handling updates the 'triggered' member of zones."""
    event = ZoneUpdate(
        included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True
    assert alarm.zones[1].triggered is False
    assert alarm.zones[2].triggered is True


def test_handle_event_zone_update_sealed(alarm: Alarm) -> None:
    """Check that ZoneUpdate handling updates pre-set 'triggered' member of zones."""
    alarm.zones[0].triggered = True
    alarm.zones[1].triggered = True

    event = ZoneUpdate(
        included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True
    assert alarm.zones[1].triggered is False
    assert alarm.zones[2].triggered is True


def test_handle_event_zone_update_callback(alarm: Alarm) -> None:
    """Check that ZoneUpdate handling causes correct on_zone_change() callbacks."""
    # Clear all zone.triggered state
    for zone in alarm.zones:
        zone.triggered = False

    # Specifically set Zone 4 triggered state to True
    alarm.zones[3].triggered = True

    cb = Mock()
    alarm.on_zone_change(cb)
    # Do Zone-Update to set zones 1 & 3 to True, all others to False
    event = ZoneUpdate(
        included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED,
    )
    alarm.handle_event(event)
    assert cb.call_count == 3
    assert cb.call_args_list[0][0] == (1, True)
    assert cb.call_args_list[1][0] == (3, True)
    assert cb.call_args_list[2][0] == (4, False)


def test_handle_event_arming_update_exit_delay(alarm: Alarm) -> None:
    """Check that ArmingUpdate initially updates the 'arming_state' to EXIT_DELAY."""
    event = ArmingUpdate(
        status=[ArmingUpdate.ArmingStatus.AREA_1_ARMED], address=None, timestamp=None
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.EXIT_DELAY


def test_handle_event_arming_update_fully_armed(alarm: Alarm) -> None:
    """Check that ArmingUpdate with FULLY_ARMED updates the 'arming_state' to ARMED."""
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


def test_handle_event_arming_update_disarmed(alarm: Alarm) -> None:
    """Check that ArmingUpdate with no state updates the 'arming_state' to DISARMED."""
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_infer_arming_state_armed_empty() -> None:
    """Check infer_arming_state works to skip ArmingUpdate with no state updates."""
    alarm = Alarm(infer_arming_state=True)
    alarm.arming_state = ArmingState.ARMED
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ARMED


def test_handle_event_arming_update_without_infer_arming_state_armed_empty() -> None:
    """Check non-infer_arming_state works to do ArmingUpdate with no state updates."""
    alarm = Alarm(infer_arming_state=False)
    alarm.arming_state = ArmingState.ARMED
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_infer_arming_state_unknown_empty() -> None:
    """Check infer_arming_state works to update Arming state to Disarmed."""
    alarm = Alarm(infer_arming_state=True)
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_callback(alarm: Alarm) -> None:
    """Check ARMED_AWAY System Status update causes on_state_change() callbacks."""
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


def test_handle_event_system_status_unsealed_zone(alarm: Alarm) -> None:
    """Check UNSEALED System Status update changes zone 'triggered' member."""
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


def test_handle_event_system_status_unsealed_zone_calls_callback(alarm: Alarm) -> None:
    """Check UNSEALED System Status update causes on_zone_change() callbacks."""
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


def test_handle_event_system_status_sealed_zone(alarm: Alarm) -> None:
    """Check SEALED System Status update changes zone 'triggered' member."""
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


def test_handle_event_system_status_sealed_zone_calls_callback(alarm: Alarm) -> None:
    """Check SEALED System Status update causes on_zone_change() callbacks."""
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


def test_handle_event_system_status_alarm(alarm: Alarm) -> None:
    """Check ALARM System Status update changes the arming-state to TRIGGERED."""
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ALARM,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.TRIGGERED


def test_handle_event_system_status_alarm_restore_while_disarmed(alarm: Alarm) -> None:
    """Check ALARM_RESTORE System Status update doesn't affect a disarmed state."""
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


def test_handle_event_system_status_alarm_restore_while_triggered(alarm: Alarm) -> None:
    """Check ALARM_RESTORE System Status update clears a triggered state to be Armed."""
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


def test_handle_event_system_status_entry_delay_start(alarm: Alarm) -> None:
    """Check ENTRY_DELAY_START System Status update sets state to ENTRY_DELAY."""
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.ENTRY_DELAY_START,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ENTRY_DELAY


def test_handle_event_system_status_entry_delay_end(alarm: Alarm) -> None:
    """
    Ensure entry delay end is ignored correctly.

    Since an additional arm event is generated, which is handled instead
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


def test_handle_event_system_status_exit_delay_start(alarm: Alarm) -> None:
    """Check EXIT_DELAY_START System Status update sets state to EXIT_DELAY."""
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.EXIT_DELAY_START,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.EXIT_DELAY


def test_handle_event_system_status_exit_delay_end_from_exit_delay(
    alarm: Alarm,
) -> None:
    """Check EXIT_DELAY_END System Status update sets state to ARMED."""
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


def test_handle_event_system_status_exit_delay_end_from_armed(alarm: Alarm) -> None:
    """Check EXIT_DELAY_END System Status update doesn't affect disarmed state."""
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


def test_handle_event_system_status_arm_events(alarm: Alarm) -> None:
    """Check all ARM System Status updates result in ARMING state."""
    for event_type in Alarm.ARM_EVENTS_MAP.keys():
        alarm.arming_state = ArmingState.DISARMED
        event = SystemStatusEvent(
            address=None, timestamp=None, type=event_type, area=0, zone=1
        )
        assert alarm.arming_state == ArmingState.DISARMED
        alarm.handle_event(event)
        assert alarm.arming_state == ArmingState.ARMING


def test_handle_event_system_status_disarmed(alarm: Alarm) -> None:
    """Check DISARMED System Status update sets state to DISARMED."""
    event = SystemStatusEvent(
        address=None,
        timestamp=None,
        type=SystemStatusEvent.EventType.DISARMED,
        area=0,
        zone=1,
    )
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_system_status_arming_delayed(alarm: Alarm) -> None:
    """Check ARMING_DELAYED System Status update does not set the arming state."""
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
def alarm() -> Alarm:
    """Set up a Alarm object as a fixture for each test."""
    return Alarm()
