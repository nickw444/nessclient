import asyncio

import click

from .. import Client, ArmingState
from ..event import BaseEvent


@click.command(help='Listen for emitted alarm events')
@click.option('--host', required=True)
@click.option('--port', required=True, type=int)
def events(host: str, port: int):
    loop = asyncio.get_event_loop()
    client = Client(host=host, port=port, loop=loop)

    @client.on_zone_change
    def on_zone_change(zone: int, triggered: bool):
        print('Zone {} changed to {}'.format(zone, triggered))

    @client.on_state_change
    def on_state_change(state: ArmingState):
        print('Alarm state changed to {}'.format(state))

    @client.on_event_received
    def on_event_received(event: BaseEvent):
        print(event)

    loop.create_task(client.keepalive())
    loop.create_task(client.update())

    loop.run_forever()
