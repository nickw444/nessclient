import asyncio

import click

from ..client import Client
from .server import DEFAULT_PORT


@click.command(help="Send a command")
@click.option("--host", default="localhost")
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--serial-tty")
@click.argument("command")
def send_command(host: str, port: int, serial_tty: str, command: str) -> None:
    loop = asyncio.get_event_loop()
    client = Client(
        host=host if serial_tty is None else None,
        port=port if serial_tty is None else None,
        serial_tty=serial_tty,
    )

    loop.run_until_complete(client.send_command(command))
    loop.run_until_complete(client.close())
    loop.close()
