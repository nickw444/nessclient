import asyncio

import click

from .server import DEFAULT_PORT


@click.command(help="Listen for emitted alarm events")
@click.option("--host", default="localhost")
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--serial-tty")
@click.option("--update-interval", type=int, default=60)
@click.option("--infer-arming-state/--no-infer-arming-state")
@click.option("--logfile", type=click.Path(), help="Write raw TX/RX packets to file")
def events(
    host: str,
    port: int,
    update_interval: int,
    infer_arming_state: bool,
    serial_tty: str | None,
    logfile: str | None,
) -> None:
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
