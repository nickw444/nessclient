import logging
import threading
import time
import uuid
from enum import Enum
from typing import Callable, List

from .aux_output import AuxOutput
from .zone import Zone

_LOGGER = logging.getLogger(__name__)


class Alarm:
    """
    Represents the complex alarm state machine
    """

    EXIT_DELAY = 10
    ENTRY_DELAY = 10

    class ArmingState(Enum):
        DISARMED = "DISARMED"
        EXIT_DELAY = "EXIT_DELAY"
        ARMED = "ARMED"
        ENTRY_DELAY = "ENTRY_DELAY"
        TRIPPED = "TRIPPED"
        PANIC = "PANIC"
        DURESS = "DURESS"
        MEDICAL = "MEDICAL"
        FIRE = "FIRE"

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
        aux_outputs: List[AuxOutput],
        _alarm_state_changed: Callable[
            [ArmingState, ArmingState, ArmingMode | None], None
        ],
        _zone_state_changed: Callable[[int, Zone.State], None],
        _aux_output_state_changed: Callable[[int, bool], None],
    ):
        self.state = state
        self.zones = zones
        self.aux_outputs = aux_outputs
        self._arming_mode: Alarm.ArmingMode | None = None
        self._alarm_state_changed = _alarm_state_changed
        self._zone_state_changed = _zone_state_changed
        self._aux_output_state_changed = _aux_output_state_changed
        self._pending_event: str | None = None
        self.exit_delay = 10
        self.entry_delay = 10

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
        aux_output_state_changed: Callable[[int, bool], None],
    ) -> "Alarm":
        return Alarm(
            state=Alarm.ArmingState.DISARMED,
            zones=Alarm._generate_zones(num_zones),
            aux_outputs=Alarm._generate_aux_outputs(),
            _alarm_state_changed=alarm_state_changed,
            _zone_state_changed=zone_state_changed,
            _aux_output_state_changed=aux_output_state_changed,
        )

    @staticmethod
    def _generate_zones(num_zones: int) -> List[Zone]:
        rv = []
        for i in range(num_zones):
            rv.append(
                Zone(id=i + 1, state=Zone.State.SEALED, in_alarm=False, in_delay=False)
            )
        return rv

    @staticmethod
    def _generate_aux_outputs() -> List[AuxOutput]:
        rv = []
        for i in range(8):
            rv.append(AuxOutput(id=i + 1, state=AuxOutput.State.OFF))
        return rv

    def arm(self, mode: ArmingMode = ArmingMode.ARMED_AWAY) -> None:
        self._update_state(Alarm.ArmingState.EXIT_DELAY, mode)
        for z in self.zones:
            z.in_alarm = False
            z.in_delay = False
        self._schedule(self.exit_delay, self._arm_complete)

    def disarm(self) -> None:
        self._cancel_pending_update()
        for z in self.zones:
            z.in_alarm = False
            z.in_delay = False
        self._update_state(Alarm.ArmingState.DISARMED, None)

    def trip(self, *, delay: bool = True, zone: int = 1) -> None:
        """
        Trip (trigger, unseal) one of the zones.

        If delay == False: zone is immediately set to 'In-Alarm' state
        If delay == False: zone is set to 'In-Delay' state, then transitions
            to 'In-Alarm' state after the standard Entry delay time
        """
        if delay:
            self._update_state_no_mode(Alarm.ArmingState.ENTRY_DELAY)
            self.zones[zone - 1].in_delay = True

            def _trip_complete() -> None:
                _LOGGER.debug("Trip completed")
                self.zones[zone - 1].in_delay = False
                self.zones[zone - 1].in_alarm = True
                self._update_state_no_mode(Alarm.ArmingState.TRIPPED)
                _LOGGER.debug("Tripped %s", self)

            self._schedule(self.entry_delay, _trip_complete)
        else:
            self._update_state_no_mode(Alarm.ArmingState.TRIPPED)
            self.zones[zone - 1].in_delay = False
            self.zones[zone - 1].in_alarm = True

    def update_zone(self, zone_id: int, state: Zone.State) -> None:
        zone = next(z for z in self.zones if z.id == zone_id)
        zone.state = state
        if self._zone_state_changed is not None:
            self._zone_state_changed(zone_id, state)

        if self.state == Alarm.ArmingState.ARMED:
            self.trip()

    def update_aux_output(self, output_id: int, active: bool) -> None:
        out = next(o for o in self.aux_outputs if o.id == output_id)
        new_state = AuxOutput.State.ON if active else AuxOutput.State.OFF
        out.state = new_state
        if self._aux_output_state_changed is not None:
            self._aux_output_state_changed(output_id, active)

    def _arm_complete(self) -> None:
        _LOGGER.debug("Arm completed")
        self._update_state_no_mode(Alarm.ArmingState.ARMED)

    def _trip_complete(self) -> None:
        _LOGGER.debug("Trip completed")
        self._update_state_no_mode(Alarm.ArmingState.TRIPPED)

    def panic(self) -> None:
        """Put alarm into Panic alarm state."""
        _LOGGER.info("setting panic")
        self._update_state_no_mode(Alarm.ArmingState.PANIC)

    def duress(self) -> None:
        """Put alarm into Duress alarm state."""
        _LOGGER.info("setting duress")
        self._cancel_pending_update()
        self._update_state_no_mode(Alarm.ArmingState.DURESS)

    def medical(self) -> None:
        """Put alarm into Medical alarm state."""
        self._update_state_no_mode(Alarm.ArmingState.MEDICAL)

    def fire(self) -> None:
        """Put alarm into Fire alarm state."""
        self._update_state_no_mode(Alarm.ArmingState.FIRE)

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

    def get_state(self) -> ArmingState:
        """Get the current Alarm State."""
        return self.state

    def get_arming_mode(self) -> ArmingMode | None:
        """Get the current Arming Mode."""
        return self._arming_mode
