import asyncio
import curses
import textwrap
from collections import deque
from contextlib import suppress
from datetime import datetime
from typing import TextIO

from ..alarm import ArmingMode, ArmingState
from ..client import Client
from ..connection import IP232Connection, Serial232Connection
from ..event import BaseEvent
from .logging_connection import LoggingConnection


async def interactive_ui(
    *,
    host: str,
    port: int,
    update_interval: int,
    infer_arming_state: bool,
    serial_tty: str | None,
    packet_logfile: str | None,
) -> None:
    """Run an interactive TUI for the alarm."""
    log_fp: TextIO | None = open(packet_logfile, "a") if packet_logfile else None
    connection = None
    if log_fp is not None:
        base_conn = (
            IP232Connection(host=host, port=port)
            if serial_tty is None
            else Serial232Connection(tty_path=serial_tty)
        )
        connection = LoggingConnection(base_conn, log_fp)

    client = Client(
        connection=connection,
        host=host if connection is None and serial_tty is None else None,
        port=port if connection is None and serial_tty is None else None,
        serial_tty=serial_tty if connection is None else None,
        infer_arming_state=infer_arming_state,
        update_interval=update_interval,
    )

    panel_version: str | None = None
    logs: deque[str] = deque(maxlen=500)
    command_buffer = ""
    status_message: str | None = None

    @client.on_event_received
    def on_event_received(event: BaseEvent) -> None:
        # Log as RX with short type/value
        try:
            pkt = event.encode()
            payload = pkt.encode()
            _add_log(logs, "RX", f"{pkt.command.name}:{pkt.data} <- {payload}")
        except Exception:
            _add_log(logs, "RX", str(event))

        # Also show the event object's repr (deserialized form)
        _add_log(logs, "EVT", repr(event))

    @client.on_zone_change
    def on_zone_change(zone: int, triggered: bool) -> None:
        # Do not append zone status updates to the events feed; the
        # zones pane already reflects current zone status.
        return

    @client.on_state_change
    def on_state_change(state: ArmingState, arming_mode: ArmingMode | None) -> None:
        _add_log(logs, "RX", f"State: {state.value} Mode: {arming_mode}")

    keepalive_task = asyncio.create_task(client.keepalive())
    # Initial update and panel info request
    _add_log(logs, "TX", "Update")
    await client.update()
    try:
        info = await client.get_panel_info()
        panel_version = f"{info.model.name} {info.version}"
        _add_log(logs, "RX", f"Panel: {panel_version}")
    except Exception as e:
        _add_log(logs, "RX", f"Failed to probe panel info: {e}")

    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    # Show cursor for input
    with suppress(Exception):
        curses.curs_set(1)
    curses.start_color()
    with suppress(Exception):
        curses.use_default_colors()
    # Colors that respect native theme
    with suppress(Exception):
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # good/ok
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # warning/RX
        curses.init_pair(3, curses.COLOR_RED, -1)  # error
        curses.init_pair(4, curses.COLOR_CYAN, -1)  # TX/info
    stdscr.nodelay(True)
    # Enable keypad to receive KEY_* codes (arrows, page up/down, mouse)
    stdscr.keypad(True)
    with suppress(Exception):
        curses.mouseinterval(0)
    # Do not capture mouse; keyboard-only scrolling
    try:
        event_scroll = 0
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()

            # Layout similar to alarm server
            bottom_h = 5
            top_h = max(3, max_y - bottom_h)
            zones_w = min(28, max(24, int(max_x * 0.28)))
            logs_w = max(10, max_x - zones_w)

            # Title/status line
            title = "Ness Events"
            state_txt = f"State: {client.alarm.arming_state.value}  Panel: {panel_version or 'unknown'}"
            stdscr.addstr(0, 1, title, curses.A_BOLD)
            if max_x > len(title) + 4:
                stdscr.addstr(0, len(title) + 3, "|")
                stdscr.addnstr(
                    0, len(title) + 5, state_txt, max(0, max_x - (len(title) + 6))
                )

            # Zones pane
            zones_h = top_h - 1
            zone_win = stdscr.derwin(zones_h, zones_w, 1, 0)
            zone_win.box()
            zone_win.addstr(0, 2, " Zones ", curses.A_BOLD)
            zone_inner_h, zone_inner_w = zones_h, zones_w
            y = 1
            for i, zone in enumerate(client.alarm.zones, start=1):
                if y >= zone_inner_h - 1:
                    break
                trig = zone.triggered
                if trig is None:
                    status = "UNKNOWN"
                    attr = curses.A_DIM | curses.color_pair(3)
                else:
                    if trig:
                        status = "UNSEALED"
                        attr = curses.A_NORMAL | curses.color_pair(2)
                    else:
                        status = "SEALED"
                        attr = curses.A_NORMAL | curses.color_pair(1)
                zone_line = f"Z{i:02d}: {status}"
                zone_win.addnstr(
                    y, 2, zone_line.ljust(zone_inner_w - 4), zone_inner_w - 4, attr
                )
                y += 1

            # Logs/messages pane
            logs_h = top_h - 1
            log_win = stdscr.derwin(logs_h, logs_w, 1, zones_w)
            log_win.box()
            log_win.addstr(0, 2, " Messages ", curses.A_BOLD)

            log_inner_w = logs_w - 2
            log_inner_h = logs_h - 2
            # Wrap and color-code logs
            wrapped_lines: list[tuple[str, int]] = []
            for line in list(logs):
                attr = curses.A_NORMAL
                if line.startswith("TX"):
                    attr |= curses.color_pair(4)
                elif line.startswith("RX"):
                    attr |= curses.color_pair(2)
                elif line.startswith("EVT"):
                    attr |= curses.A_DIM
                pieces = textwrap.wrap(
                    line,
                    width=log_inner_w,
                    break_long_words=True,
                    break_on_hyphens=True,
                ) or [""]
                for p in pieces:
                    wrapped_lines.append((p, attr))
            max_scroll = max(0, len(wrapped_lines) - log_inner_h)
            event_scroll = min(event_scroll, max_scroll)
            start = max(0, len(wrapped_lines) - log_inner_h - event_scroll)
            visible = wrapped_lines[start : start + log_inner_h]
            for idx, (txt, attr) in enumerate(visible):
                log_win.addnstr(idx + 1, 1, txt.ljust(log_inner_w), log_inner_w, attr)

            # Input pane
            input_win = stdscr.derwin(bottom_h, max_x, top_h, 0)
            input_win.box()
            input_win.addstr(0, 2, " Input ", curses.A_BOLD)
            legend = [
                "Commands: a=arm_away h=arm_home d [code] u=update q=quit",
                "Arrow/PgUp/PgDn/Home/End to scroll messages",
            ]
            for i, line in enumerate(legend):
                if 1 + i >= bottom_h - 2:
                    break
                input_win.addnstr(1 + i, 2, line, max(0, max_x - 4))

            # Status message
            if status_message:
                input_win.addnstr(
                    bottom_h - 3, 2, status_message, max(0, max_x - 4), curses.A_DIM
                )

            # Prompt
            prompt = "> "
            max_input = max(0, max_x - len(prompt) - 4)
            display = command_buffer[-max_input:]
            input_win.addnstr(bottom_h - 2, 2, prompt + display, max(0, max_x - 4))
            with suppress(Exception):
                input_win.move(
                    bottom_h - 2, min(2 + len(prompt) + len(display), max_x - 2)
                )

            for win in (zone_win, log_win, input_win):
                win.noutrefresh()
            curses.doupdate()
            # Drain input events to keep interaction snappy
            had_input = False
            while True:
                ch = stdscr.getch()
                if ch == -1:
                    break
                had_input = True
                if ch in (10, 13):
                    cmd = command_buffer.strip()
                    command_buffer = ""
                    if cmd:
                        lower = cmd.lower()
                        if lower in {"q", "quit", "exit"}:
                            break
                        elif lower in {"a", "arm", "away", "arm_away"}:
                            _add_log(logs, "TX", "Arm Away")
                            await client.arm_away()
                        elif lower in {"h", "home", "arm_home"}:
                            _add_log(logs, "TX", "Arm Home")
                            await client.arm_home()
                        elif lower.startswith("d"):
                            parts = lower.split()
                            code = parts[1] if len(parts) > 1 else "1234"
                            _add_log(logs, "TX", f"Disarm {'*' * len(code)}")
                            await client.disarm(code)
                        elif lower in {"u", "update"}:
                            _add_log(logs, "TX", "Update")
                            await client.update()
                        else:
                            status_message = f"Unknown command: {cmd}"
                elif ch in (curses.KEY_BACKSPACE, 127, 8):
                    command_buffer = command_buffer[:-1]
                elif ch == curses.KEY_UP:
                    event_scroll = min(event_scroll + 1, max_scroll)
                elif ch == curses.KEY_DOWN:
                    event_scroll = max(event_scroll - 1, 0)
                elif ch == curses.KEY_PPAGE:
                    event_scroll = min(event_scroll + log_inner_h, max_scroll)
                elif ch == curses.KEY_NPAGE:
                    event_scroll = max(event_scroll - log_inner_h, 0)
                elif ch == curses.KEY_HOME:
                    event_scroll = max_scroll
                elif ch == curses.KEY_END:
                    event_scroll = 0
                elif 0 <= ch <= 255:
                    # Only accept printable characters into the input buffer
                    if 32 <= ch <= 126:
                        command_buffer += chr(ch)
            if not had_input:
                await asyncio.sleep(0.05)
    finally:
        keepalive_task.cancel()
        with suppress(asyncio.CancelledError):
            await keepalive_task
        await client.close()
        if log_fp is not None:
            log_fp.close()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


def _add_log(logs: deque[str], direction: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    logs.append(f"{direction} {ts} | {message}")
