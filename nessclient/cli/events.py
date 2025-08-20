import asyncio
import click

from ..client import Client
from ..alarm import ArmingState, ArmingMode
from ..event import BaseEvent
from .server import DEFAULT_PORT


@click.command(help="Listen for emitted alarm events")
@click.option("--host", default="localhost")
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--serial-tty")
@click.option("--update-interval", type=int, default=60)
@click.option("--infer-arming-state/--no-infer-arming-state")
@click.option("--interactive", is_flag=True, help="Run with terminal UI")
def events(
    host: str,
    port: int,
    update_interval: int,
    infer_arming_state: bool,
    serial_tty: str | None,
    interactive: bool,
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
            )
        )
        return

    loop = asyncio.get_event_loop()
    client = Client(
        host=host if serial_tty is None else None,
        port=port if serial_tty is None else None,
        serial_tty=serial_tty,
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

    loop.create_task(client.keepalive())
    loop.create_task(client.update())

    loop.run_forever()
