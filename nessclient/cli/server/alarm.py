import logging
import threading
import time
import uuid
from enum import Enum
from typing import List, Callable

from .zone import Zone

_LOGGER = logging.getLogger(__name__)

EXIT_DELAY = 10
ENTRY_DELAY = 10


class Alarm:
    """
    Represents the complex alarm state machine
    """

    class ArmingState(Enum):
        DISARMED = "DISARMED"
        EXIT_DELAY = "EXIT_DELAY"
        ARMED = "ARMED"
        ENTRY_DELAY = "ENTRY_DELAY"
        TRIPPED = "TRIPPED"

    class ArmingMode(Enum):
        ARMED_AWAY = "ARMED_AWAY"
        ARMED_HOME = "ARMED_HOME"
        ARMED_DAY = "ARMED_DAY"
        ARMED_NIGHT = "ARMED_NIGHT"
        ARMED_VACATION = "ARMED_VACATION"

    def __init__(
        self,
        state: ArmingState,
        zones: List[Zone],
        _alarm_state_changed: Callable[
            [ArmingState, ArmingState, ArmingMode | None], None
        ],
        _zone_state_changed: Callable[[int, Zone.State], None],
    ):
        self.state = state
        self.zones = zones
        self._arming_mode: Alarm.ArmingMode | None = None
        self._alarm_state_changed = _alarm_state_changed
        self._zone_state_changed = _zone_state_changed
        self._pending_event: str | None = None

    @property
    def arming_mode(self) -> "Alarm.ArmingMode | None":
        return self._arming_mode

    @staticmethod
    def create(
        num_zones: int,
        alarm_state_changed: Callable[
            [ArmingState, ArmingState, ArmingMode | None], None
        ],
        zone_state_changed: Callable[[int, Zone.State], None],
    ) -> "Alarm":
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

    def arm(self, mode: ArmingMode = ArmingMode.ARMED_AWAY) -> None:
        self._update_state(Alarm.ArmingState.EXIT_DELAY, mode)
        self._schedule(EXIT_DELAY, self._arm_complete)

    def disarm(self) -> None:
        self._cancel_pending_update()
        self._update_state(Alarm.ArmingState.DISARMED, None)

    def trip(self) -> None:
        self._update_state_no_mode(Alarm.ArmingState.ENTRY_DELAY)
        self._schedule(ENTRY_DELAY, self._trip_complete)

    def update_zone(self, zone_id: int, state: Zone.State) -> None:
        zone = next(z for z in self.zones if z.id == zone_id)
        zone.state = state
        if self._zone_state_changed is not None:
            self._zone_state_changed(zone_id, state)

        if self.state == Alarm.ArmingState.ARMED:
            self.trip()

    def _arm_complete(self) -> None:
        _LOGGER.debug("Arm completed")
        self._update_state_no_mode(Alarm.ArmingState.ARMED)

    def _trip_complete(self) -> None:
        _LOGGER.debug("Trip completed")
        self._update_state_no_mode(Alarm.ArmingState.TRIPPED)

    def _cancel_pending_update(self) -> None:
        if self._pending_event is not None:
            self._pending_event = None

    def _schedule(self, delay: int, fn: Callable[[], None]) -> None:
        self._cancel_pending_update()
        event = uuid.uuid4().hex
        self._pending_event = event

        def _run() -> None:
            time.sleep(delay)
            if event == self._pending_event:
                fn()

        threading.Thread(target=_run).start()

    def _update_state(
        self,
        state: ArmingState,
        arming_mode: ArmingMode | None,
    ) -> None:
        if self._alarm_state_changed is not None:
            self._alarm_state_changed(self.state, state, arming_mode)

        self.state = state
        self._arming_mode = arming_mode

    def _update_state_no_mode(
        self,
        state: ArmingState,
    ) -> None:
        if self._alarm_state_changed is not None:
            self._alarm_state_changed(self.state, state, self._arming_mode)

        self.state = state
