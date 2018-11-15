import logging
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import List, Callable, Optional

from .zone import Zone

_LOGGER = logging.getLogger(__name__)

EXIT_DELAY = 10
ENTRY_DELAY = 10


@dataclass
class Alarm:
    """
    Represents the complex alarm state machine
    """

    class ArmingState(Enum):
        DISARMED = 'DISARMED'
        EXIT_DELAY = 'EXIT_DELAY'
        ARMED_AWAY = 'ARMED_AWAY'
        ENTRY_DELAY = 'ENTRY_DELAY'
        TRIPPED = 'TRIPPED'

    state: ArmingState
    zones: List[Zone]

    _alarm_state_changed: Callable[[ArmingState, ArmingState], None]
    _zone_state_changed: Callable[[int, Zone.State], None]

    _pending_event: Optional[str] = None

    @staticmethod
    def create(num_zones: int,
               alarm_state_changed: Callable[[ArmingState, ArmingState], None],
               zone_state_changed: Callable[[int, Zone.State], None]) -> 'Alarm':
        return Alarm(
            state=Alarm.ArmingState.DISARMED,
            zones=Alarm._generate_zones(num_zones),
            _alarm_state_changed=alarm_state_changed,
            _zone_state_changed=zone_state_changed,
        )

    @staticmethod
    def _generate_zones(num_zones: int) -> List[Zone]:
        rv = []
        for i in range(num_zones):
            rv.append(Zone(id=i + 1, state=Zone.State.SEALED))
        return rv

    def arm(self):
        self._update_state(Alarm.ArmingState.EXIT_DELAY)
        self._schedule(EXIT_DELAY, self._arm_complete)

    def disarm(self):
        self._cancel_pending_update()
        self._update_state(Alarm.ArmingState.DISARMED)

    def trip(self):
        self._update_state(Alarm.ArmingState.ENTRY_DELAY)
        self._schedule(ENTRY_DELAY, self._trip_complete)

    def update_zone(self, zone_id: int, state: Zone.State):
        zone = next(z for z in self.zones if z.id == zone_id)
        zone.state = state
        if self._zone_state_changed is not None:
            self._zone_state_changed(zone_id, state)

        if self.state == Alarm.ArmingState.ARMED_AWAY:
            self.trip()

    def _arm_complete(self):
        _LOGGER.debug("Arm completed")
        self._update_state(Alarm.ArmingState.ARMED_AWAY)

    def _trip_complete(self):
        _LOGGER.debug("Trip completed")
        self._update_state(Alarm.ArmingState.TRIPPED)

    def _cancel_pending_update(self):
        if self._pending_event is not None:
            self._pending_event = None

    def _schedule(self, delay, fn):
        self._cancel_pending_update()
        event = uuid.uuid4().hex
        self._pending_event = event

        def _run():
            time.sleep(delay)
            if event == self._pending_event:
                fn()

        threading.Thread(target=_run).start()

    def _update_state(self, state: ArmingState):
        if self._alarm_state_changed is not None:
            self._alarm_state_changed(self.state, state)

        self.state = state
