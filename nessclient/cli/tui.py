import asyncio
import curses
from contextlib import suppress

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

    @client.on_event_received
    def on_event_received(event: BaseEvent) -> None:
        nonlocal panel_version
        if isinstance(event, PanelVersionUpdate):
            panel_version = (
                f"{event.model.name} {event.major_version}.{event.minor_version}"
            )

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
            stdscr.addstr(0, 0, "Ness Alarm Interactive")
            stdscr.addstr(1, 0, f"Panel: {panel_version or 'unknown'}")
            stdscr.addstr(2, 0, f"State: {client.alarm.arming_state.value}")
            for i, zone in enumerate(client.alarm.zones, 1):
                triggered = zone.triggered
                if triggered is None:
                    status = "UNKNOWN"
                else:
                    status = "UNSEALED" if triggered else "SEALED"
                stdscr.addstr(2 + i, 0, f"Zone {i:02d}: {status}")
            command_row = 3 + len(client.alarm.zones)
            stdscr.addstr(
                command_row,
                0,
                "Commands: A=Arm Away H=Arm Home D=Disarm U=Update Q=Quit",
            )
            stdscr.refresh()
            await asyncio.sleep(0.1)
            ch = stdscr.getch()
            if ch == -1:
                continue
            if ch in (ord("q"), ord("Q")):
                break
            if ch in (ord("a"), ord("A")):
                await client.arm_away()
            elif ch in (ord("h"), ord("H")):
                await client.arm_home()
            elif ch in (ord("d"), ord("D")):
                await client.disarm("1234")
            elif ch in (ord("u"), ord("U")):
                await client.update()
    finally:
        keepalive_task.cancel()
        with suppress(asyncio.CancelledError):
            await keepalive_task
        await client.close()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
