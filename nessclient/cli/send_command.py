import asyncio

import click

from ..client import Client
from .server import DEFAULT_PORT


@click.command(help="Send a command")
@click.option("--host", default="localhost")
@click.option("--port", type=int, default=DEFAULT_PORT)
@click.option("--serial-tty", help="Serial port path or serialx URL")
@click.argument("command")
def send_command(host: str, port: int, serial_tty: str, command: str) -> None:
    asyncio.run(_send_command(host, port, serial_tty, command))


async def _send_command(host: str, port: int, serial_tty: str, command: str) -> None:
    client = Client(
        host=host if serial_tty is None else None,
        port=port if serial_tty is None else None,
        serial_tty=serial_tty,
    )
    try:
        await client.send_command(command)
    finally:
        await client.close()
