import asyncio
from nessclient import Client, ArmingState, ArmingMode, BaseEvent

host = "127.0.0.1"
port = 65432


def main(timeout: int = 0) -> None:
    loop = asyncio.get_event_loop()
    client = Client(host=host, port=port)

    @client.on_zone_change
    def on_zone_change(zone: int, triggered: bool) -> None:
        print("Zone {} changed to {}".format(zone, triggered))

    @client.on_state_change
    def on_state_change(state: ArmingState, mode: ArmingMode | None) -> None:
        print("Alarm state changed to {}".format(state))

    @client.on_event_received
    def on_event_received(event: BaseEvent) -> None:
        print("Event received:", event)

    task_group: asyncio.futures.Future[tuple[None, None, None]]

    async def canceller(timeout: float) -> None:
        if timeout != 0:
            await asyncio.sleep(timeout)
            task_group.cancel()

    task_group = asyncio.gather(
        canceller(timeout),
        client.keepalive(),
        client.update(),
    )

    try:
        loop.run_until_complete(task_group)
    except asyncio.exceptions.CancelledError:
        pass  # cancelled

    loop.run_until_complete(client.close())


if __name__ == "__main__":
    main()
