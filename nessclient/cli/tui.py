import asyncio
import curses
import textwrap
from collections import deque
from contextlib import suppress

from ..alarm import ArmingMode, ArmingState
from ..client import Client
from ..event import BaseEvent, PanelVersionUpdate


async def interactive_ui(
    *,
    host: str,
    port: int,
    update_interval: int,
    infer_arming_state: bool,
    serial_tty: str | None,
) -> None:
    """Run an interactive TUI for the alarm."""
    client = Client(
        host=host if serial_tty is None else None,
        port=port if serial_tty is None else None,
        serial_tty=serial_tty,
        infer_arming_state=infer_arming_state,
        update_interval=update_interval,
    )

    panel_version: str | None = None
    events: deque[str] = deque(maxlen=100)
    command_buffer = ""

    @client.on_event_received
    def on_event_received(event: BaseEvent) -> None:
        nonlocal panel_version
        events.append(str(event))
        if isinstance(event, PanelVersionUpdate):
            panel_version = (
                f"{event.model.name} {event.major_version}.{event.minor_version}"
            )

    @client.on_zone_change
    def on_zone_change(zone: int, triggered: bool) -> None:
        # Do not append zone status updates to the events feed; the
        # zones pane already reflects current zone status.
        return

    @client.on_state_change
    def on_state_change(state: ArmingState, arming_mode: ArmingMode | None) -> None:
        events.append(f"State changed to {state.value}")

    keepalive_task = asyncio.create_task(client.keepalive())
    # Log and perform initial update and command
    events.append("-> Send: Update")
    await client.update()
    events.append("-> Send: S17")
    await client.send_command("S17")

    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
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

            # Input has two inner rows: prompt and command hints
            input_height = 4
            # State pane has two content rows: arming + panel info
            state_height = 4
            # Remove footer/info pane and allocate remaining space to content
            content_height = max_y - (input_height + state_height)
            zone_inner_width = 20
            zone_width = zone_inner_width + 2
            event_width = max_x - zone_width
            event_inner_width = event_width - 2
            content_inner_height = content_height - 2

            state_win = stdscr.derwin(state_height, max_x, 0, 0)
            event_win = stdscr.derwin(content_height, event_width, state_height, 0)
            zone_win = stdscr.derwin(
                content_height, zone_width, state_height, event_width
            )
            input_win = stdscr.derwin(
                input_height, max_x, state_height + content_height, 0
            )

            for win in (state_win, event_win, zone_win, input_win):
                win.box()

            # Add titles to panes
            state_win.addstr(0, 2, " State ")
            event_win.addstr(0, 2, " Events ")
            zone_win.addstr(0, 2, " Zones ")
            input_win.addstr(0, 2, " Input ")

            state_win.addstr(
                1, 1, f"Arming: {client.alarm.arming_state.value}"[: max_x - 2]
            )
            state_win.addstr(2, 1, f"Panel: {panel_version or 'unknown'}"[: max_x - 2])

            for i, zone in enumerate(client.alarm.zones, start=0):
                if i >= content_inner_height:
                    break
                triggered = zone.triggered
                if triggered is None:
                    status = "UNKNOWN"
                else:
                    status = "UNSEALED" if triggered else "SEALED"
                zone_win.addstr(i + 1, 1, f"Z{i + 1:02d}: {status}")

            # Wrap event messages to fit within the events pane
            wrapped_lines: list[str] = []
            for line in list(events):
                pieces = textwrap.wrap(
                    line,
                    width=event_inner_width,
                    break_long_words=True,
                    break_on_hyphens=True,
                ) or [""]
                wrapped_lines.extend(pieces)
            max_scroll = max(0, len(wrapped_lines) - content_inner_height)
            event_scroll = min(event_scroll, max_scroll)
            start = max(0, len(wrapped_lines) - content_inner_height - event_scroll)
            visible_lines = wrapped_lines[start : start + content_inner_height]
            for idx, line in enumerate(visible_lines):
                event_win.addstr(idx + 1, 1, line[:event_inner_width])

            input_win.addstr(1, 1, f"> {command_buffer}"[: max_x - 2])
            # Show command hints inside the input pane (second inner row)
            commands_help = "Commands: a/arm_away, h/arm_home, d [code], u/update, q/quit"
            input_win.addstr(2, 1, commands_help[: max_x - 2])
            # No footer/info pane; panel info is shown in the State pane

            for win in (state_win, event_win, zone_win, input_win):
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
                            events.append("-> Send: Arm Away")
                            await client.arm_away()
                        elif lower in {"h", "home", "arm_home"}:
                            events.append("-> Send: Arm Home")
                            await client.arm_home()
                        elif lower.startswith("d"):
                            parts = lower.split()
                            code = parts[1] if len(parts) > 1 else "1234"
                            events.append(f"-> Send: Disarm {'*' * len(code)}")
                            await client.disarm(code)
                        elif lower in {"u", "update"}:
                            events.append("-> Send: Update")
                            await client.update()
                        else:
                            events.append(f"Unknown command: {cmd}")
                elif ch in (curses.KEY_BACKSPACE, 127, 8):
                    command_buffer = command_buffer[:-1]
                elif ch == curses.KEY_UP:
                    event_scroll = min(event_scroll + 1, max_scroll)
                elif ch == curses.KEY_DOWN:
                    event_scroll = max(event_scroll - 1, 0)
                elif ch == curses.KEY_PPAGE:
                    event_scroll = min(event_scroll + content_inner_height, max_scroll)
                elif ch == curses.KEY_NPAGE:
                    event_scroll = max(event_scroll - content_inner_height, 0)
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
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
