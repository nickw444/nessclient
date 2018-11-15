import asyncio

import click

from ..client import Client
from ..connection import IP232Connection


@click.command(help="Send a command")
@click.option('--host', required=True)
@click.option('--port', required=True)
@click.argument('command')
def send_command(host, port, command):
    loop = asyncio.get_event_loop()

    connection = IP232Connection(host=host, port=port, loop=loop)
    client = Client(connection=connection)

    loop.run_until_complete(client.send_command(command))
    client.close()
    loop.close()
