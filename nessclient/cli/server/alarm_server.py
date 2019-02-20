import logging
import random
import threading
import time
from typing import List

from .alarm import Alarm
from .server import Server, get_zone_state_event_type
from .zone import Zone
from ...event import SystemStatusEvent, ArmingUpdate, ZoneUpdate, StatusUpdate

_LOGGER = logging.getLogger(__name__)


class AlarmServer():
    def __init__(self, host: str, port: int):
        self._alarm = Alarm.create(
            num_zones=8,
            alarm_state_changed=self._alarm_state_changed,
            zone_state_changed=self._zone_state_changed,
        )
        self._server = Server(handle_command=self._handle_command)
        self._host = host
        self._port = port
        self._simulation_running = False

    def start(self):
        self._server.start(host=self._host, port=self._port)
        self._start_simulation()

        while True:
            command = input("Command: ")
            if command is None:
                continue

            command = command.upper().strip()
            if command == "D":
                self._alarm.disarm()
            elif command == "A":
                self._alarm.arm()
            elif command == "T":
                self._alarm.trip()

            print(command)

    def _alarm_state_changed(self, previous_state: Alarm.ArmingState,
                             state: Alarm.ArmingState):
        if state != Alarm.ArmingState.DISARMED:
            self._stop_simulation()

        for event_type in get_events_for_state_update(previous_state, state):
            event = SystemStatusEvent(
                type=event_type,
                zone=0x00,
                area=0x00,
                timestamp=None,
                address=0
            )
            self._server.write_event(event)

    def _zone_state_changed(self, zone_id: int, state: Zone.State):
        event = SystemStatusEvent(
            type=get_zone_state_event_type(state),
            zone=zone_id,
            area=0,
            timestamp=None,
            address=0
        )
        self._server.write_event(event)

    def _handle_command(self, command: str):
        _LOGGER.info("Incoming User Command: {}".format(command))
        if command == 'AE' or command == 'A1234E':
            self._alarm.arm()
        elif command == '1234E':
            self._alarm.disarm()
        elif command == 'S00':
            self._handle_zone_input_unsealed_status_update_request()
        elif command == 'S14':
            self._handle_arming_status_update_request()

    def _handle_arming_status_update_request(self):
        event = ArmingUpdate(
            status=get_arming_status(self._alarm.state),
            address=0x00,
            timestamp=None,
        )
        self._server.write_event(event)

    def _handle_zone_input_unsealed_status_update_request(self):
        event = ZoneUpdate(
            request_id=StatusUpdate.RequestID.ZONE_INPUT_UNSEALED,
            included_zones=[
                get_zone_for_id(z.id) for z in
                self._alarm.zones if z.state == Zone.State.UNSEALED],
            address=0x00,
            timestamp=None,
        )
        self._server.write_event(event)

    def _simulate_zone_events(self):
        while self._simulation_running:
            zone: Zone = random.choice(self._alarm.zones)
            self._alarm.update_zone(zone.id, toggled_state(zone.state))
            _LOGGER.info("Toggled zone: %s", zone)
            time.sleep(random.randint(1, 5))

    def _stop_simulation(self):
        self._simulation_running = False

    def _start_simulation(self):
        if not self._simulation_running:
            self._simulation_running = True
            threading.Thread(target=self._simulate_zone_events).start()


def get_events_for_state_update(
        previous_state: Alarm.ArmingState,
        state: Alarm.ArmingState) -> List[SystemStatusEvent.EventType]:

    if state == Alarm.ArmingState.DISARMED:
        yield SystemStatusEvent.EventType.DISARMED
    if state == Alarm.ArmingState.EXIT_DELAY:
        yield SystemStatusEvent.EventType.ARMED_AWAY
        yield SystemStatusEvent.EventType.EXIT_DELAY_START

    if state == Alarm.ArmingState.TRIPPED:
        yield SystemStatusEvent.EventType.ALARM

    # When state transitions from EXIT_DELAY, trigger EXIT_DELAY_END.
    if (previous_state == Alarm.ArmingState.EXIT_DELAY and state != previous_state or
            state == Alarm.ArmingState.ARMED_AWAY):
        yield SystemStatusEvent.EventType.EXIT_DELAY_END

    if state == Alarm.ArmingState.ENTRY_DELAY:
        yield SystemStatusEvent.EventType.ENTRY_DELAY_START

    # When state transitions from ENTRY_DELAY, trigger ENTRY_DELAY_END
    if previous_state == Alarm.ArmingState.ENTRY_DELAY and state != previous_state:
        yield SystemStatusEvent.EventType.ENTRY_DELAY_END


def get_arming_status(state: Alarm.ArmingState) -> List[ArmingUpdate.ArmingStatus]:
    if state == Alarm.ArmingState.ARMED_AWAY:
        return [
            ArmingUpdate.ArmingStatus.AREA_1_ARMED,
            ArmingUpdate.ArmingStatus.AREA_1_FULLY_ARMED
        ]
    elif state == Alarm.ArmingState.EXIT_DELAY:
        return [ArmingUpdate.ArmingStatus.AREA_1_ARMED]
    else:
        return []


def toggled_state(state: Zone.State) -> Zone.State:
    if state == Zone.State.SEALED:
        return Zone.State.UNSEALED
    else:
        return Zone.State.SEALED


def get_zone_for_id(zone_id: int) -> ZoneUpdate.Zone:
    key = 'ZONE_{}'.format(zone_id)
    return ZoneUpdate.Zone[key]
