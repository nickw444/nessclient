import curses
import logging
import random
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Deque, Iterator, List, Optional

from .alarm import Alarm
from .server import Server, get_zone_state_event_type
from .zone import Zone
from ...event import (
    SystemStatusEvent,
    ArmingUpdate,
    ZoneUpdate_1_16,
    ZoneUpdate_17_32,
    StatusUpdate,
    PanelVersionUpdate,
)

_LOGGER = logging.getLogger(__name__)


class AlarmServer:
    def __init__(
        self,
        host: str,
        port: int,
        num_zones: int,
        panel_model: PanelVersionUpdate.Model,
        panel_major_version: int,
        panel_minor_version: int,
    ):
        self._alarm = Alarm.create(
            num_zones=num_zones,
            alarm_state_changed=self._alarm_state_changed,
            zone_state_changed=self._zone_state_changed,
        )
        self._server = Server(
            handle_command=self._handle_command,
            log_callback=self._on_server_log,
            rx_callback=self._on_server_rx,
        )
        self._host = host
        self._port = port
        self._simulation_running = False
        self._panel_model = panel_model
        self._panel_major_version = panel_major_version
        self._panel_minor_version = panel_minor_version
        # UI state
        self._logs: Deque[str] = deque(maxlen=500)
        self._input_buffer: str = ""
        self._status_message: Optional[str] = None
        self._stop_flag = threading.Event()

    def start(self) -> None:
        self._server.start(host=self._host, port=self._port)
        curses.wrapper(self._run_ui)

    def _run_ui(self, stdscr: Any) -> None:
        curses.curs_set(1)
        curses.start_color()
        try:
            curses.use_default_colors()
        except Exception:
            pass
        # Define a few simple color pairs that play nicely with terminal theme
        try:
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_CYAN, -1)
        except Exception:
            # On terminals without color support, ignore
            pass

        stdscr.nodelay(True)
        stdscr.keypad(True)
        self._stop_flag.clear()
        while not self._stop_flag.is_set():
            self._draw_ui(stdscr)
            ch = stdscr.getch()
            if ch == -1:
                time.sleep(0.05)
                continue
            if ch in (3, 4):  # Ctrl+C/Ctrl+D
                break
            handled = self._handle_keypress(ch)
            if not handled:
                # fall back small sleep to avoid tight loop
                time.sleep(0.01)
        self._stop_simulation()

    def _draw_ui(self, stdscr: Any) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()

        # Layout sizes
        bottom_h = 5
        top_h = max(3, height - bottom_h)
        zones_w = min(28, max(24, int(width * 0.28)))
        log_w = max(10, width - zones_w)

        # Top title/status line (no border)
        title = "Ness Alarm Server"
        mode = self._alarm.arming_mode.value if self._alarm.arming_mode else "-"
        status = f"State: {self._alarm.state.value}  Mode: {mode}  Panel: {self._panel_model.value} {self._panel_major_version}.{self._panel_minor_version}"
        stdscr.addstr(0, 1, title, curses.A_BOLD)
        stdscr.addstr(0, min(len(title) + 3, width - 1), "|")
        stdscr.addnstr(
            0, min(len(title) + 5, width - 1), status, max(0, width - (len(title) + 6))
        )

        # Zones window with border
        zones_h = top_h - 1
        zones_win = stdscr.derwin(zones_h, zones_w, 1, 0)
        zones_win.box()
        self._draw_zones(zones_win)

        # Logs window with border
        logs_h = top_h - 1
        logs_win = stdscr.derwin(logs_h, log_w, 1, zones_w)
        logs_win.box()
        self._draw_logs(logs_win)

        # Bottom input/legend window with border
        input_win = stdscr.derwin(bottom_h, width, top_h, 0)
        input_win.box()
        self._draw_input(input_win)

        stdscr.refresh()

    def _draw_zones(self, win: Any) -> None:
        win_height, win_width = win.getmaxyx()
        # Title
        win.addstr(0, 2, " Zones ", curses.A_BOLD)
        # Content area starts at (1,1) inside border
        y = 1
        for z in self._alarm.zones:
            if y >= win_height - 1:
                break
            label = f"{z.id:>2}: {z.state.value}"
            attr = curses.A_NORMAL
            if z.state == Zone.State.SEALED:
                attr |= curses.color_pair(1)
            elif z.state == Zone.State.UNSEALED:
                attr |= curses.color_pair(2)
            # TRIPPED isn't a zone state; ALARM reflects global, but keep red for emphasis where useful
            win.addnstr(y, 2, label.ljust(win_width - 4), win_width - 4, attr)
            y += 1

    def _draw_logs(self, win: Any) -> None:
        win_height, win_width = win.getmaxyx()
        win.addstr(0, 2, " Messages ", curses.A_BOLD)
        # Show the latest lines, clipped to window height - 2 (for borders)
        max_lines = max(0, win_height - 2)
        lines = list(self._logs)[-max_lines:]
        start_y = 1
        for i, line in enumerate(lines):
            attr = curses.A_NORMAL
            if line.startswith("TX"):
                attr |= curses.color_pair(4)
            elif line.startswith("RX"):
                attr |= curses.color_pair(2)
            elif line.startswith("ERR"):
                attr |= curses.color_pair(3)
            win.addnstr(start_y + i, 1, line.ljust(win_width - 2), win_width - 2, attr)

    def _draw_input(self, win: Any) -> None:
        win_height, win_width = win.getmaxyx()
        win.addstr(0, 2, " Input ", curses.A_BOLD)
        # Legend area
        legend_lines = [
            "Commands: a=away h=home n=night v=vac d=disarm t=trip s=sim on/off",
            f"Toggle zone: type number then Enter (1-{len(self._alarm.zones)})    q=quit",
        ]
        for i, line in enumerate(legend_lines):
            if 1 + i >= win_height - 2:
                break
            win.addnstr(1 + i, 2, line, max(0, win_width - 4))

        # Status message (if any)
        if self._status_message:
            msg = self._status_message
            win.addnstr(
                win_height - 3,
                2,
                msg[: max(0, win_width - 4)],
                max(0, win_width - 4),
                curses.A_DIM,
            )

        # Input prompt on the last line
        prompt = "> "
        max_input = max(0, win_width - len(prompt) - 4)
        display = self._input_buffer[-max_input:]
        win.addnstr(win_height - 2, 2, prompt + display, max(0, win_width - 4))
        # Place cursor at end
        try:
            win.move(win_height - 2, min(2 + len(prompt) + len(display), win_width - 2))
        except Exception:
            pass

    def _handle_keypress(self, ch: int) -> bool:
        """Handle keypress. Returns True if handled."""
        # Handle special keys
        if ch in (ord("q"), ord("Q")):
            self._stop_flag.set()
            return True
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            if self._input_buffer:
                self._input_buffer = self._input_buffer[:-1]
            return True
        if ch in (10, 13):  # Enter
            self._execute_command(self._input_buffer.strip())
            self._input_buffer = ""
            return True

        # Single-key shortcuts (also log status)
        if ch in (ord("d"), ord("D")):
            self._alarm.disarm()
            self._set_status("Disarmed")
            return True
        if ch in (ord("a"), ord("A")):
            self._alarm.arm(Alarm.ArmingMode.ARMED_AWAY)
            self._set_status("Arming: Away")
            return True
        if ch in (ord("h"), ord("H")):
            self._alarm.arm(Alarm.ArmingMode.ARMED_HOME)
            self._set_status("Arming: Home")
            return True
        if ch in (ord("n"), ord("N")):
            self._alarm.arm(Alarm.ArmingMode.ARMED_NIGHT)
            self._set_status("Arming: Night")
            return True
        if ch in (ord("v"), ord("V")):
            self._alarm.arm(Alarm.ArmingMode.ARMED_VACATION)
            self._set_status("Arming: Vacation")
            return True
        if ch in (ord("t"), ord("T")):
            self._alarm.trip()
            self._set_status("Alarm tripped")
            return True
        if ch in (ord("s"), ord("S")):
            self._toggle_simulation()
            return True
        # Numeric toggles are handled via the input buffer + Enter to support multi-digit zones

        # Printable characters go to input buffer
        if 32 <= ch <= 126:
            self._input_buffer += chr(ch)
            return True

        return False

    def _execute_command(self, cmd: str) -> None:
        if not cmd:
            return
        lc = cmd.lower()
        if lc in ("d", "disarm"):
            self._alarm.disarm()
            self._set_status("Disarmed")
            return
        if lc in ("a", "away"):
            self._alarm.arm(Alarm.ArmingMode.ARMED_AWAY)
            self._set_status("Arming: Away")
            return
        if lc in ("h", "home"):
            self._alarm.arm(Alarm.ArmingMode.ARMED_HOME)
            self._set_status("Arming: Home")
            return
        if lc in ("n", "night"):
            self._alarm.arm(Alarm.ArmingMode.ARMED_NIGHT)
            self._set_status("Arming: Night")
            return
        if lc in ("v", "vac", "vacation"):
            self._alarm.arm(Alarm.ArmingMode.ARMED_VACATION)
            self._set_status("Arming: Vacation")
            return
        if lc in ("t", "trip"):
            self._alarm.trip()
            self._set_status("Alarm tripped")
            return
        # Simulation controls
        if lc in ("s", "sim", "simulate"):
            self._toggle_simulation()
            return
        if lc in ("s on", "sim on", "simulate on"):
            self._toggle_simulation(True)
            return
        if lc in ("s off", "sim off", "simulate off"):
            self._toggle_simulation(False)
            return
        if lc.isdigit():
            zone_id = int(lc)
            zone = next((z for z in self._alarm.zones if z.id == zone_id), None)
            if zone is not None:
                new_state = (
                    Zone.State.UNSEALED
                    if zone.state == Zone.State.SEALED
                    else Zone.State.SEALED
                )
                self._alarm.update_zone(zone_id, new_state)
                self._set_status(f"Toggled zone {zone_id}")
                return
        self._set_status(f"Unknown command: {cmd}")

    def _set_status(self, msg: str) -> None:
        self._status_message = msg

        # Clear after a short delay, without blocking UI
        def _clear() -> None:
            time.sleep(2.0)
            # Only clear if the message hasn't changed
            if self._status_message == msg:
                self._status_message = None

        threading.Thread(target=_clear, daemon=True).start()

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
            self._log_tx_event(event)
            self._server.write_event(event)

    def _zone_state_changed(self, zone_id: int, state: Zone.State) -> None:
        event = SystemStatusEvent(
            type=get_zone_state_event_type(state),
            zone=zone_id,
            area=0,
            timestamp=None,
            address=0,
        )
        self._log_tx_event(event)
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
            self._handle_zone_1_16_input_unsealed_status_update_request()
        elif command == "S20":
            self._handle_zone_17_32_input_unsealed_status_update_request()
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
        self._log_tx_event(event)
        self._server.write_event(event)

    def _handle_zone_1_16_input_unsealed_status_update_request(self) -> None:
        event = ZoneUpdate_1_16(
            request_id=StatusUpdate.RequestID.ZONE_1_16_INPUT_UNSEALED,
            included_zones=[
                get_zone_for_id_1_16(z.id)
                for z in self._alarm.zones[:16]
                if z.state == Zone.State.UNSEALED
            ],
            address=0x00,
            timestamp=None,
        )
        self._log_tx_event(event)
        self._server.write_event(event)

    def _handle_zone_17_32_input_unsealed_status_update_request(self) -> None:
        event = ZoneUpdate_17_32(
            request_id=StatusUpdate.RequestID.ZONE_17_32_INPUT_UNSEALED,
            included_zones=[
                get_zone_for_id_17_32(z.id)
                for z in self._alarm.zones[16:32]
                if z.state == Zone.State.UNSEALED
            ],
            address=0x00,
            timestamp=None,
        )
        self._log_tx_event(event)
        self._server.write_event(event)

    def _handle_panel_version_update_request(self) -> None:
        event = PanelVersionUpdate(
            model=self._panel_model,
            major_version=self._panel_major_version,
            minor_version=self._panel_minor_version,
            address=0x00,
            timestamp=None,
        )
        self._log_tx_event(event)
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
            threading.Thread(target=self._simulate_zone_events, daemon=True).start()

    def _toggle_simulation(self, on: Optional[bool] | None = None) -> None:
        desired = (not self._simulation_running) if on is None else on
        if desired and not self._simulation_running:
            self._start_simulation()
            self._set_status("Simulation: ON")
        elif not desired and self._simulation_running:
            self._stop_simulation()
            self._set_status("Simulation: OFF")

    def _add_log(self, direction: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._logs.append(f"{direction} {ts} | {message}")

    def _add_log_multiline(self, direction: str, text: str) -> None:
        for line in text.splitlines():
            self._add_log(direction, line)

    def _log_tx_event(self, event: Any) -> None:
        try:
            pkt = event.encode()
            encoded = pkt.encode()
            self._add_log("TX", f"{pkt.command.name}:{pkt.data} -> {encoded}")
        except Exception:
            self._add_log("TX", repr(event))

    def _on_server_log(self, message: str) -> None:
        # Surface server errors in the UI log area
        self._add_log_multiline("ERR", message)

    def _on_server_rx(self, line: str, pkt: Optional[Any]) -> None:
        # Show the full ASCII RX line and decoded command/data (if available)
        if pkt is not None:
            try:
                parsed = f"{pkt.command.name}:{pkt.data}"
            except Exception:
                parsed = "<unknown>"
            self._add_log("RX", f"{line} -> {parsed}")
        else:
            self._add_log("RX", line)


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


def get_zone_for_id_1_16(zone_id: int) -> ZoneUpdate_1_16.Zone:
    key = "ZONE_{}".format(zone_id)
    return ZoneUpdate_1_16.Zone[key]


def get_zone_for_id_17_32(zone_id: int) -> ZoneUpdate_17_32.Zone:
    key = "ZONE_{}".format(zone_id)
    return ZoneUpdate_17_32.Zone[key]
