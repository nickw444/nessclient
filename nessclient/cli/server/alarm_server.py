import curses
import logging
import random
import threading
import time
from typing import Any, List, Iterator

from .alarm import Alarm
from .server import Server, get_zone_state_event_type
from .zone import Zone
from ...event import (
    SystemStatusEvent,
    ArmingUpdate,
    ZoneUpdate,
    StatusUpdate,
    PanelVersionUpdate,
)

_LOGGER = logging.getLogger(__name__)


class AlarmServer:
    def __init__(
        self,
        host: str,
        port: int,
        panel_model: PanelVersionUpdate.Model,
        panel_major_version: int,
        panel_minor_version: int,
    ):
        self._alarm = Alarm.create(
            num_zones=8,
            alarm_state_changed=self._alarm_state_changed,
            zone_state_changed=self._zone_state_changed,
        )
        self._server = Server(handle_command=self._handle_command)
        self._host = host
        self._port = port
        self._simulation_running = False
        self._panel_model = panel_model
        self._panel_major_version = panel_major_version
        self._panel_minor_version = panel_minor_version

    def start(self) -> None:
        self._server.start(host=self._host, port=self._port)
        self._start_simulation()
        curses.wrapper(self._run_ui)

    def _run_ui(self, stdscr: Any) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        while True:
            self._draw_ui(stdscr)
            ch = stdscr.getch()
            if ch == -1:
                time.sleep(0.1)
                continue
            if ch in (ord("q"), ord("Q")):
                break
            if ch in (ord("d"), ord("D")):
                self._alarm.disarm()
            elif ch in (ord("a"), ord("A")):
                self._alarm.arm(Alarm.ArmingMode.ARMED_AWAY)
            elif ch in (ord("h"), ord("H")):
                self._alarm.arm(Alarm.ArmingMode.ARMED_HOME)
            elif ch in (ord("n"), ord("N")):
                self._alarm.arm(Alarm.ArmingMode.ARMED_NIGHT)
            elif ch in (ord("v"), ord("V")):
                self._alarm.arm(Alarm.ArmingMode.ARMED_VACATION)
            elif ch in (ord("t"), ord("T")):
                self._alarm.trip()
            elif ord("1") <= ch <= ord("0") + len(self._alarm.zones):
                zone_id = ch - ord("0")
                zone = next(z for z in self._alarm.zones if z.id == zone_id)
                new_state = (
                    Zone.State.UNSEALED
                    if zone.state == Zone.State.SEALED
                    else Zone.State.SEALED
                )
                self._alarm.update_zone(zone_id, new_state)
        self._stop_simulation()

    def _draw_ui(self, stdscr: Any) -> None:
        stdscr.erase()
        mode = self._alarm.arming_mode.value if self._alarm.arming_mode else "-"
        stdscr.addstr(0, 0, f"Alarm state: {self._alarm.state.value}")
        stdscr.addstr(1, 0, f"Mode: {mode}")
        stdscr.addstr(3, 0, "Zones:")
        for i, z in enumerate(self._alarm.zones):
            stdscr.addstr(4 + i, 2, f"{z.id}: {z.state.value}")
        row = 4 + len(self._alarm.zones) + 1
        stdscr.addstr(
            row,
            0,
            "d=disarm a=away h=home n=night v=vac t=trip q=quit",
        )
        stdscr.addstr(row + 1, 0, "Toggle zones with 1-{}".format(len(self._alarm.zones)))
        stdscr.refresh()

    def _alarm_state_changed(
        self,
        previous_state: Alarm.ArmingState,
        state: Alarm.ArmingState,
        arming_mode: Alarm.ArmingMode | None,
    ) -> None:
        if state != Alarm.ArmingState.DISARMED:
            self._stop_simulation()

        for event_type in get_events_for_state_update(previous_state, state, arming_mode):
            event = SystemStatusEvent(
                type=event_type, zone=0x00, area=0x00, timestamp=None, address=0
            )
            self._server.write_event(event)

    def _zone_state_changed(self, zone_id: int, state: Zone.State) -> None:
        event = SystemStatusEvent(
            type=get_zone_state_event_type(state),
            zone=zone_id,
            area=0,
            timestamp=None,
            address=0,
        )
        self._server.write_event(event)

    def _handle_command(self, command: str) -> None:
        _LOGGER.info("Incoming User Command: {}".format(command))
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
        elif command == "S17":
            self._handle_panel_version_update_request()

    def _handle_arming_status_update_request(self) -> None:
        event = ArmingUpdate(
            status=get_arming_status(self._alarm.state),
            address=0x00,
            timestamp=None,
        )
        self._server.write_event(event)

    def _handle_zone_input_unsealed_status_update_request(self) -> None:
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

    def _handle_panel_version_update_request(self) -> None:
        event = PanelVersionUpdate(
            model=self._panel_model,
            major_version=self._panel_major_version,
            minor_version=self._panel_minor_version,
            address=0x00,
            timestamp=None,
        )
        self._server.write_event(event)

    def _simulate_zone_events(self) -> None:
        while self._simulation_running:
            zone: Zone = random.choice(self._alarm.zones)
            self._alarm.update_zone(zone.id, toggled_state(zone.state))
            _LOGGER.info("Toggled zone: %s", zone)
            time.sleep(random.randint(1, 5))

    def _stop_simulation(self) -> None:
        self._simulation_running = False

    def _start_simulation(self) -> None:
        if not self._simulation_running:
            self._simulation_running = True
            threading.Thread(target=self._simulate_zone_events).start()


def mode_to_event(mode: Alarm.ArmingMode | None) -> SystemStatusEvent.EventType:
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


def get_arming_status(state: Alarm.ArmingState) -> List[ArmingUpdate.ArmingStatus]:
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
    if state == Zone.State.SEALED:
        return Zone.State.UNSEALED
    else:
        return Zone.State.SEALED


def get_zone_for_id(zone_id: int) -> ZoneUpdate.Zone:
    key = "ZONE_{}".format(zone_id)
    return ZoneUpdate.Zone[key]
