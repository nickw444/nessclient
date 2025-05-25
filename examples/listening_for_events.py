import asyncio

from nessclient import Client, ArmingState, BaseEvent

host = '172.0.0.1'
port = 4999
client = Client(host=host, port=port)


@client.on_zone_change
def on_zone_change(zone: int, triggered: bool):
    print('Zone {} changed to {}'.format(zone, triggered))


@client.on_state_change
def on_state_change(state: ArmingState):
    print('Alarm state changed to {}'.format(state))


@client.on_event_received
def on_event_received(event: BaseEvent):
    print('Event received:', event)


async def main():
    await asyncio.gather(
        client.keepalive(),
        client.update(),
    )
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
