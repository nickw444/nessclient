"""Implements a test alarm emulator with an interactive CLI UI."""

import logging
import random
import threading
import time
from typing import Iterator

from .alarm import Alarm
from .server import Server, get_zone_state_event_type
from .zone import Zone
from ...event import SystemStatusEvent, ArmingUpdate, ZoneUpdate, StatusUpdate

_LOGGER = logging.getLogger(__name__)


class AlarmServer:
    """Implements a test alarm emulator with an interactive CLI UI."""

    def __init__(self, host: str, port: int) -> None:
        """Create a new test alarm emulator that listens on a specifc host+port."""
        self._alarm = Alarm.create(
            num_zones=8,
            alarm_state_changed=self._alarm_state_changed,
            zone_state_changed=self._zone_state_changed,
        )
        self._server = Server(handle_command=self._handle_command)
        self._host = host
        self._port = port
        self._simulation_running = False

    def start(self) -> None:
        """Start running the test alarm emulator."""
        self._server.start(host=self._host, port=self._port)
        self._start_simulation()

        while True:
            command = input("Command: ")
            if command is None:
                continue

            command = command.upper().strip()
            if command == "D":
                self._alarm.disarm()
            elif command == "A" or command == "AA":
                self._alarm.arm(Alarm.ArmingMode.ARMED_AWAY)
            elif command == "AH":
                self._alarm.arm(Alarm.ArmingMode.ARMED_HOME)
            elif command == "AD":
                self._alarm.arm(Alarm.ArmingMode.ARMED_DAY)
            elif command == "AN":
                self._alarm.arm(Alarm.ArmingMode.ARMED_NIGHT)
            elif command == "AV":
                self._alarm.arm(Alarm.ArmingMode.ARMED_VACATION)
            elif command == "T":
                self._alarm.trip()

            print(command)

    def _alarm_state_changed(
        self,
        previous_state: Alarm.ArmingState,
        state: Alarm.ArmingState,
        arming_mode: Alarm.ArmingMode | None,
    ) -> None:
        """
        Handle zone arming status changes.

        Sends a System Status Event packet to indicate the change
        """
        if state != Alarm.ArmingState.DISARMED:
            self._stop_simulation()

        for event_type in get_events_for_state_update(
            previous_state, state, arming_mode
        ):
            event = SystemStatusEvent(
                type=event_type, zone=0x00, area=0x00, timestamp=None, address=0
            )
            self._server.write_event(event)

    def _zone_state_changed(self, zone_id: int, state: Zone.State) -> None:
        """
        Handle zone sealed/unsealed changes.

        Sends a System Status Event packet to indicate the change
        """
        event = SystemStatusEvent(
            type=get_zone_state_event_type(state),
            zone=zone_id,
            area=0,
            timestamp=None,
            address=0,
        )
        self._server.write_event(event)

    def _handle_command(self, command: str) -> None:
        """
        Responds to commands from a TCP client.

        This is the main function that handles incoming packets.

        Handles Arm, Arm-Home, Disarm, Unsealed-Status & Arming-Status requests
        """
        _LOGGER.info("Incoming User Command: {}".format(command))

        # NOTE: No defined way to set Armed-Night mode, Armed-Vacation
        #       or Armed-Highest in the manual
        if command == "AE" or command == "A1234E":
            self._alarm.arm()
        elif command == "HE" or command == "H1234E":
            self._alarm.arm(Alarm.ArmingMode.ARMED_HOME)
        elif command == "1234E":
            self._alarm.disarm()
        elif command == "S00":
            self._handle_zone_input_unsealed_status_update_request()
        elif command == "S14":
            self._handle_arming_status_update_request()

    def _handle_arming_status_update_request(self) -> None:
        """
        Handle a "S14" (arming state) status update request.

        Sends a Status Update response packet to indicate the current arming state.
        """
        event = ArmingUpdate(
            status=get_arming_status(self._alarm.state),
            address=0x00,
            timestamp=None,
        )
        self._server.write_event(event)

    def _handle_zone_input_unsealed_status_update_request(self) -> None:
        """
        Handle a "S00" (zone unsealed state) status update request.

        Sends a Status Update response packet to indicate the current sealed states.
        """
        event = ZoneUpdate(
            request_id=StatusUpdate.RequestID.ZONE_INPUT_UNSEALED,
            included_zones=[
                get_zone_for_id(z.id)
                for z in self._alarm.zones
                if z.state == Zone.State.UNSEALED
            ],
            address=0x00,
            timestamp=None,
        )
        self._server.write_event(event)

    def _simulate_zone_events(self) -> None:
        """
        Thread that randomly toggles the sealed/unsealed state of a random zones.

        Toggles in a loop with pauses of 1-5 seconds between each
        """
        while self._simulation_running:
            zone: Zone = random.choice(self._alarm.zones)
            self._alarm.update_zone(zone.id, toggled_state(zone.state))
            _LOGGER.info("Toggled zone: %s", zone)
            time.sleep(random.randint(1, 5))

    def _stop_simulation(self) -> None:
        """Stop the sealed/unsealed random toggling."""
        self._simulation_running = False

    def _start_simulation(self) -> None:
        """Start the sealed/unsealed random toggling."""
        if not self._simulation_running:
            self._simulation_running = True
            threading.Thread(target=self._simulate_zone_events).start()


def mode_to_event(mode: Alarm.ArmingMode | None) -> SystemStatusEvent.EventType:
    """Convert a Alarm.ArmingMode to a SystemStatusEvent.EventType mode."""
    if mode == Alarm.ArmingMode.ARMED_AWAY:
        return SystemStatusEvent.EventType.ARMED_AWAY
    elif mode == Alarm.ArmingMode.ARMED_HOME:
        return SystemStatusEvent.EventType.ARMED_HOME
    elif mode == Alarm.ArmingMode.ARMED_DAY:
        return SystemStatusEvent.EventType.ARMED_DAY
    elif mode == Alarm.ArmingMode.ARMED_NIGHT:
        return SystemStatusEvent.EventType.ARMED_NIGHT
    elif mode == Alarm.ArmingMode.ARMED_VACATION:
        return SystemStatusEvent.EventType.ARMED_VACATION
    else:
        raise AssertionError("Unknown alarm mode")


def get_events_for_state_update(
    previous_state: Alarm.ArmingState,
    state: Alarm.ArmingState,
    arming_mode: Alarm.ArmingMode | None,
) -> Iterator[SystemStatusEvent.EventType]:
    """Determine which async events should be sent upon state changes."""
    if state == Alarm.ArmingState.DISARMED:
        yield SystemStatusEvent.EventType.DISARMED
    if state == Alarm.ArmingState.EXIT_DELAY:
        yield mode_to_event(arming_mode)
        yield SystemStatusEvent.EventType.EXIT_DELAY_START

    if state == Alarm.ArmingState.TRIPPED:
        yield SystemStatusEvent.EventType.ALARM

    # When state transitions from EXIT_DELAY, trigger EXIT_DELAY_END.
    if (
        previous_state == Alarm.ArmingState.EXIT_DELAY
        and state != previous_state
        or state == Alarm.ArmingState.ARMED
    ):
        yield SystemStatusEvent.EventType.EXIT_DELAY_END

    if state == Alarm.ArmingState.ENTRY_DELAY:
        yield SystemStatusEvent.EventType.ENTRY_DELAY_START

    # When state transitions from ENTRY_DELAY, trigger ENTRY_DELAY_END
    if previous_state == Alarm.ArmingState.ENTRY_DELAY and state != previous_state:
        yield SystemStatusEvent.EventType.ENTRY_DELAY_END


def get_arming_status(state: Alarm.ArmingState) -> list[ArmingUpdate.ArmingStatus]:
    """
    Get a list of ArmingStatus items for the current armed status.

    Appropriate to pass to ArmingUpdate() constructor
    """
    if state == Alarm.ArmingState.ARMED:
        return [
            ArmingUpdate.ArmingStatus.AREA_1_ARMED,
            ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED,
        ]
    elif state == Alarm.ArmingState.EXIT_DELAY:
        return [ArmingUpdate.ArmingStatus.AREA_1_ARMED]
    else:
        return []


def toggled_state(state: Zone.State) -> Zone.State:
    """Invert the supplied sealed/unsealed zone state."""
    if state == Zone.State.SEALED:
        return Zone.State.UNSEALED
    else:
        return Zone.State.SEALED


def get_zone_for_id(zone_id: int) -> ZoneUpdate.Zone:
    """Get the zone details matching the supplied zone ID."""
    key = "ZONE_{}".format(zone_id)
    return ZoneUpdate.Zone[key]
