import asyncio

from nessclient import Client, ArmingState, ArmingMode, BaseEvent


async def main() -> None:
    host = "127.0.0.1"
    port = 65432
    client = Client(host=host, port=port)

    @client.on_zone_change
    def on_zone_change(zone: int, triggered: bool) -> None:
        print("Zone {} changed to {}".format(zone, triggered))

    @client.on_state_change
    def on_state_change(state: ArmingState, _arming_mode: ArmingMode | None) -> None:
        print("Alarm state changed to {}".format(state))

    @client.on_event_received
    def on_event_received(event: BaseEvent) -> None:
        print("Event received:", event)

    try:
        await asyncio.gather(
            client.keepalive(),
            client.update(),
        )
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
