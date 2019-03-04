from unittest.mock import Mock

import pytest

from nessclient.alarm import Alarm, ArmingState
from nessclient.event import ArmingUpdate, ZoneUpdate, SystemStatusEvent


def test_state_is_initially_unknown(alarm):
    assert alarm.arming_state == ArmingState.UNKNOWN


def test_zones_are_initially_unknown(alarm):
    for zone in alarm.zones:
        assert zone.triggered is None


def test_16_zones_are_created(alarm):
    assert len(alarm.zones) == 16


def test_handle_event_zone_update(alarm):
    event = ZoneUpdate(
        included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED)
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True
    assert alarm.zones[1].triggered is False
    assert alarm.zones[2].triggered is True


def test_handle_event_zone_update_sealed(alarm):
    alarm.zones[0].triggered = True
    alarm.zones[1].triggered = True

    event = ZoneUpdate(
        included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED)
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True
    assert alarm.zones[1].triggered is False
    assert alarm.zones[2].triggered is True


def test_handle_event_zone_update_callback(alarm):
    for zone in alarm.zones:
        zone.triggered = False
    alarm.zones[3].triggered = True

    cb = Mock()
    alarm.on_zone_change(cb)
    event = ZoneUpdate(
        included_zones=[ZoneUpdate.Zone.ZONE_1, ZoneUpdate.Zone.ZONE_3],
        timestamp=None,
        address=None,
        request_id=ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED)
    alarm.handle_event(event)
    assert cb.call_count == 3
    assert cb.call_args_list[0][0] == (1, True)
    assert cb.call_args_list[1][0] == (3, True)
    assert cb.call_args_list[2][0] == (4, False)


def test_handle_event_arming_update_exit_delay(alarm):
    event = ArmingUpdate(status=[ArmingUpdate.ArmingStatus.AREA_1_ARMED],
                         address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.EXIT_DELAY


def test_handle_event_arming_update_fully_armed(alarm):
    event = ArmingUpdate(status=[
        ArmingUpdate.ArmingStatus.AREA_1_ARMED,
        ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED], address=None,
        timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.ARMED


def test_handle_event_arming_update_disarmed(alarm):
    event = ArmingUpdate(status=[], address=None, timestamp=None)
    alarm.handle_event(event)
    assert alarm.arming_state == ArmingState.DISARMED


def test_handle_event_arming_update_callback(alarm):
    cb = Mock()
    alarm.on_state_change(cb)
    event = ArmingUpdate(status=[ArmingUpdate.ArmingStatus.AREA_1_ARMED],
                         address=None, timestamp=None)
    alarm.handle_event(event)
    assert cb.call_count == 1
    assert cb.call_args[0] == (ArmingState.EXIT_DELAY,)


def test_handle_event_system_status_unsealed_zone(alarm):
    alarm.zones[0].triggered = False

    event = SystemStatusEvent(address=None, timestamp=None,
                              type=SystemStatusEvent.EventType.UNSEALED,
                              area=0, zone=1)
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is True


def test_handle_event_system_status_unsealed_zone_calls_callback(alarm):
    alarm.zones[0].triggered = False

    cb = Mock()
    alarm.on_zone_change(cb)
    event = SystemStatusEvent(address=None, timestamp=None,
                              type=SystemStatusEvent.EventType.UNSEALED,
                              area=0, zone=1)
    alarm.handle_event(event)
    assert cb.call_count == 1
    assert cb.call_args[0] == (1, True)


def test_handle_event_system_status_sealed_zone(alarm):
    alarm.zones[0].triggered = True

    event = SystemStatusEvent(address=None, timestamp=None,
                              type=SystemStatusEvent.EventType.SEALED,
                              area=0, zone=1)
    alarm.handle_event(event)
    assert alarm.zones[0].triggered is False


def test_handle_event_system_status_sealed_zone_calls_callback(alarm):
    alarm.zones[0].triggered = True

    cb = Mock()
    alarm.on_zone_change(cb)
    event = SystemStatusEvent(address=None, timestamp=None,
                              type=SystemStatusEvent.EventType.SEALED,
                              area=0, zone=1)
    alarm.handle_event(event)
    assert cb.call_count == 1
    assert cb.call_args[0] == (1, False)


@pytest.fixture
def alarm():
    return Alarm()
