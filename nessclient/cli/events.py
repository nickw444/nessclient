import asyncio
from typing import TextIO

import click

from ..alarm import ArmingMode, ArmingState
from ..client import Client
from ..connection import IP232Connection, Serial232Connection
from ..event import BaseEvent
from .logging_connection import LoggingConnection
from .server import DEFAULT_PORT


@click.command(help="Listen for emitted alarm events")
@click.option("--host", default="localhost")
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--serial-tty")
@click.option("--update-interval", type=int, default=60)
@click.option("--infer-arming-state/--no-infer-arming-state")
@click.option("--interactive", is_flag=True, help="Run with terminal UI")
@click.option("--logfile", type=click.Path(), help="Write raw TX/RX packets to file")
def events(
    host: str,
    port: int,
    update_interval: int,
    infer_arming_state: bool,
    serial_tty: str | None,
    interactive: bool,
    logfile: str | None,
) -> None:
    if interactive:
        from .tui import interactive_ui

        asyncio.run(
            interactive_ui(
                host=host,
                port=port,
                update_interval=update_interval,
                infer_arming_state=infer_arming_state,
                serial_tty=serial_tty,
                packet_logfile=logfile,
            )
        )
        return

    log_fp: TextIO | None = open(logfile, "a") if logfile else None
    connection = None
    if log_fp is not None:
        base_conn = (
            IP232Connection(host=host, port=port)
            if serial_tty is None
            else Serial232Connection(tty_path=serial_tty)
        )
        connection = LoggingConnection(base_conn, log_fp)

    loop = asyncio.get_event_loop()
    client = Client(
        connection=connection,
        host=host if connection is None and serial_tty is None else None,
        port=port if connection is None and serial_tty is None else None,
        serial_tty=serial_tty if connection is None else None,
        infer_arming_state=infer_arming_state,
        update_interval=update_interval,
    )

    @client.on_zone_change
    def on_zone_change(zone: int, triggered: bool) -> None:
        print(f"Zone {zone} changed to {triggered}")

    @client.on_state_change
    def on_state_change(state: ArmingState, arming_mode: ArmingMode | None) -> None:
        print(f"Alarm state changed to {state} (mode: {arming_mode})")

    @client.on_event_received
    def on_event_received(event: BaseEvent) -> None:
        print(event)

    async def _init_panel_info() -> None:
        try:
            info = await client.get_panel_info()
            print(f"Panel: {info.model.name} {info.version}")
        except Exception as e:
            # Non-fatal; continue receiving events
            print(f"Failed to probe panel info: {e}")

    loop.create_task(client.keepalive())
    loop.create_task(client.update())
    loop.create_task(_init_panel_info())

    loop.run_forever()
