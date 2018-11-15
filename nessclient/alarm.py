from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, List

from .event import BaseEvent, ZoneUpdate, ArmingUpdate, SystemStatusEvent


class ArmingState(Enum):
    UNKNOWN = 'UNKNOWN'
    DISARMED = 'DISARMED'
    ARMING = 'ARMING'
    EXIT_DELAY = 'EXIT_DELAY'
    ARMED = 'ARMED'
    ENTRY_DELAY = 'ENTRY_DELAY'
    TRIGGERED = 'TRIGGERED'


class Alarm:
    """
    In-memory representation of the state of the alarm the client is connected to.

    TODO(NW): Handle output state events to determine when alarm is on/off
    """
    ARM_EVENTS = [
        SystemStatusEvent.EventType.ARMED_AWAY,
        SystemStatusEvent.EventType.ARMED_HOME,
        SystemStatusEvent.EventType.ARMED_DAY,
        SystemStatusEvent.EventType.ARMED_NIGHT,
        SystemStatusEvent.EventType.ARMED_VACATION,
        SystemStatusEvent.EventType.ARMED_HIGHEST
    ]

    @dataclass
    class Zone:
        triggered: Optional[bool]

    def __init__(self) -> None:
        self.arming_state: ArmingState = ArmingState.UNKNOWN
        self.zones: List[Alarm.Zone] = [Alarm.Zone(triggered=None) for _ in range(16)]

        self._on_state_change: Optional[Callable[['ArmingState'], None]] = None
        self._on_zone_change: Optional[Callable[[int, bool], None]] = None

    def handle_event(self, event: BaseEvent) -> None:
        if isinstance(event, ArmingUpdate):
            self._handle_arming_update(event)
        elif (isinstance(event, ZoneUpdate)
              and event.request_id == ZoneUpdate.RequestID.ZONE_INPUT_UNSEALED):
            self._handle_zone_input_update(event)
        elif isinstance(event, SystemStatusEvent):
            self._handle_system_status_event(event)

    def _handle_arming_update(self, update: ArmingUpdate) -> None:
        if ArmingUpdate.ArmingStatus.AREA_1_ARMED in update.status:
            return self._update_arming_state(ArmingState.ARMED)
        else:
            return self._update_arming_state(ArmingState.DISARMED)

    def _handle_zone_input_update(self, update: ZoneUpdate) -> None:
        for i, zone in enumerate(self.zones):
            zone_id = i + 1
            name = 'ZONE_{}'.format(zone_id)
            if ZoneUpdate.Zone[name] in update.included_zones:
                self._update_zone(zone_id, True)
            else:
                self._update_zone(zone_id, False)

    def _handle_system_status_event(self, event: SystemStatusEvent) -> None:
        """
        DISARMED -> ARMED_AWAY -> EXIT_DELAY_START -> EXIT_DELAY_END
         (trip): -> ALARM -> OUTPUT_ON -> ALARM_RESTORE
            (disarm): -> DISARMED -> OUTPUT_OFF
         (disarm): -> DISARMED
         (disarm before EXIT_DELAY_END): -> DISARMED -> EXIT_DELAY_END

        TODO(NW): Check ALARM_RESTORE state transition to move back into ARMED_AWAY state
        """
        if event.type == SystemStatusEvent.EventType.UNSEALED:
            return self._update_zone(event.zone, True)
        elif event.type == SystemStatusEvent.EventType.SEALED:
            return self._update_zone(event.zone, False)
        elif event.type == SystemStatusEvent.EventType.ALARM:
            return self._update_arming_state(ArmingState.TRIGGERED)
        elif event.type == SystemStatusEvent.EventType.ALARM_RESTORE:
            return self._update_arming_state(ArmingState.ARMED)
        elif event.type == SystemStatusEvent.EventType.ENTRY_DELAY_START:
            return self._update_arming_state(ArmingState.ENTRY_DELAY)
        elif event.type == SystemStatusEvent.EventType.ENTRY_DELAY_END:
            pass
        elif event.type == SystemStatusEvent.EventType.EXIT_DELAY_START:
            return self._update_arming_state(ArmingState.EXIT_DELAY)
        elif event.type == SystemStatusEvent.EventType.EXIT_DELAY_END:
            # Exit delay finished - if we were in the process of arming update
            # state to armed
            if self.arming_state == ArmingState.EXIT_DELAY:
                self._update_arming_state(ArmingState.ARMED)
        elif event.type in Alarm.ARM_EVENTS:
            return self._update_arming_state(ArmingState.ARMING)
        elif event.type == SystemStatusEvent.EventType.DISARMED:
            return self._update_arming_state(ArmingState.DISARMED)
        elif event.type == SystemStatusEvent.EventType.ARMING_DELAYED:
            pass

    def _update_arming_state(self, state: 'ArmingState') -> None:
        if self._on_state_change is not None and self.arming_state != state:
            self.arming_state = state
            self._on_state_change(state)

    def _update_zone(self, zone_id: int, state: bool) -> None:
        zone = self.zones[zone_id - 1]
        if self._on_zone_change is not None and zone.triggered != state:
            zone.triggered = state
            self._on_zone_change(zone_id, state)
