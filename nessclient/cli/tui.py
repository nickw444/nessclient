import asyncio
import curses
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
        status = "UNSEALED" if triggered else "SEALED"
        events.append(f"Zone {zone:02d} {status}")

    @client.on_state_change
    def on_state_change(state: ArmingState, arming_mode: ArmingMode | None) -> None:
        events.append(f"State changed to {state.value}")

    keepalive_task = asyncio.create_task(client.keepalive())
    await client.update()
    await client.send_command("S17")

    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    stdscr.nodelay(True)
    try:
        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()

            footer_height = 3
            input_height = 3
            state_height = 3
            content_height = max_y - (footer_height + input_height + state_height)
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
            footer_win = stdscr.derwin(
                footer_height, max_x, state_height + content_height + input_height, 0
            )

            for win in (state_win, event_win, zone_win, input_win, footer_win):
                win.box()

            state_win.addstr(1, 1, f"Arming: {client.alarm.arming_state.value}")

            for i, zone in enumerate(client.alarm.zones, start=1):
                if i > content_inner_height:
                    break
                triggered = zone.triggered
                if triggered is None:
                    status = "UNKNOWN"
                else:
                    status = "UNSEALED" if triggered else "SEALED"
                zone_win.addstr(i + 1, 1, f"Z{i:02d}: {status}")

            visible_events = list(events)[-content_inner_height:]
            for idx, line in enumerate(visible_events):
                event_win.addstr(idx + 1, 1, line[:event_inner_width])

            input_win.addstr(1, 1, f"> {command_buffer}"[: max_x - 2])
            footer_win.addstr(1, 1, f"Panel: {panel_version or 'unknown'}")

            for win in (state_win, event_win, zone_win, input_win, footer_win):
                win.noutrefresh()
            curses.doupdate()
            await asyncio.sleep(0.1)
            ch = stdscr.getch()
            if ch == -1:
                continue
            if ch in (10, 13):
                cmd = command_buffer.strip()
                command_buffer = ""
                if cmd:
                    lower = cmd.lower()
                    if lower in {"q", "quit", "exit"}:
                        break
                    elif lower in {"a", "arm", "away", "arm_away"}:
                        await client.arm_away()
                    elif lower in {"h", "home", "arm_home"}:
                        await client.arm_home()
                    elif lower.startswith("d"):
                        parts = lower.split()
                        code = parts[1] if len(parts) > 1 else "1234"
                        await client.disarm(code)
                    elif lower in {"u", "update"}:
                        await client.update()
                    else:
                        events.append(f"Unknown command: {cmd}")
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                command_buffer = command_buffer[:-1]
            elif 0 <= ch <= 255:
                command_buffer += chr(ch)
    finally:
        keepalive_task.cancel()
        with suppress(asyncio.CancelledError):
            await keepalive_task
        await client.close()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
