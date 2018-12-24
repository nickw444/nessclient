import asyncio

import click

from ..client import Client


@click.command(help="Send a command")
@click.option('--host', required=True)
@click.option('--port', required=True, type=int)
@click.argument('command')
def send_command(host: str, port: int, command: str):
    loop = asyncio.get_event_loop()
    client = Client(host=host, port=port, loop=loop)

    loop.run_until_complete(client.send_command(command))
    loop.run_until_complete(client.close())
    loop.close()
