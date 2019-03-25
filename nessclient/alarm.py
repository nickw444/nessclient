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
    In-memory representation of the state of the alarm the client is connected
    to.
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

    def __init__(self, infer_arming_state: bool = False) -> None:
        self._infer_arming_state = infer_arming_state
        self.arming_state: ArmingState = ArmingState.UNKNOWN
        self.zones: List[Alarm.Zone] = [Alarm.Zone(triggered=None) for _ in
                                        range(16)]

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
        if update.status == [ArmingUpdate.ArmingStatus.AREA_1_ARMED]:
            return self._update_arming_state(ArmingState.EXIT_DELAY)
        if ArmingUpdate.ArmingStatus.AREA_1_ARMED in update.status and \
                ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED in update.status:
            return self._update_arming_state(ArmingState.ARMED)
        else:
            if self._infer_arming_state:
                # State inference is enabled. Therefore the arming state can
                # only be reverted to disarmed via a system status event.
                # This works around a bug with some panels (<v5.8) which emit
                # update.status = [] when they are armed.
                # TODO(NW): It would be ideal to find a better way to
                #  query this information on-demand, but for now this should
                #  resolve the issue.
                if self.arming_state == ArmingState.UNKNOWN:
                    return self._update_arming_state(ArmingState.DISARMED)
            else:
                # State inference is disabled, therefore we can assume the
                # panel is "disarmed" as it did not have any arming flags set
                # in the arming update status as per the documentation.
                # Note: This may not be correct and may not correctly represent
                # other modes of arming other than ARMED_AWAY.
                # TODO(NW): Perform some testing to determine how the client
                #  handles other arming modes.
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
            if self.arming_state != ArmingState.DISARMED:
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
                return self._update_arming_state(ArmingState.ARMED)
        elif event.type in Alarm.ARM_EVENTS:
            return self._update_arming_state(ArmingState.ARMING)
        elif event.type == SystemStatusEvent.EventType.DISARMED:
            return self._update_arming_state(ArmingState.DISARMED)
        elif event.type == SystemStatusEvent.EventType.ARMING_DELAYED:
            pass

    def _update_arming_state(self, state: 'ArmingState') -> None:
        if self.arming_state != state:
            self.arming_state = state
            if self._on_state_change is not None:
                self._on_state_change(state)

    def _update_zone(self, zone_id: int, state: bool) -> None:
        zone = self.zones[zone_id - 1]
        if zone.triggered != state:
            zone.triggered = state
            if self._on_zone_change is not None:
                self._on_zone_change(zone_id, state)

    def on_state_change(self, f: Callable[[ArmingState], None]) -> None:
        self._on_state_change = f

    def on_zone_change(self, f: Callable[[int, bool], None]) -> None:
        self._on_zone_change = f
