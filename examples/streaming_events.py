import asyncio

from nessclient import Client


async def main() -> None:
    client = Client(host="127.0.0.1", port=65432)
    events = client.stream_events()
    state_changes = client.stream_state_changes()
    zone_changes = client.stream_zone_changes()
    output_changes = client.stream_aux_output_changes()

    async def print_events() -> None:
        async for event in events:
            print("Event received:", event)

    async def print_state_changes() -> None:
        async for state, mode in state_changes:
            print("State changed:", state, mode)

    async def print_zone_changes() -> None:
        async for zone_id, triggered in zone_changes:
            print("Zone {} changed to {}".format(zone_id, triggered))

    async def print_output_changes() -> None:
        async for output_id, active in output_changes:
            print(f"Output {output_id} changed to {active}")

    tasks = [
        asyncio.create_task(client.keepalive()),
        asyncio.create_task(print_events()),
        asyncio.create_task(print_state_changes()),
        asyncio.create_task(print_zone_changes()),
        asyncio.create_task(print_output_changes()),
    ]

    try:
        # Allow handlers to start, then request an initial state update.
        await asyncio.sleep(0)
        await client.update()
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()
        await events.aclose()
        await state_changes.aclose()
        await zone_changes.aclose()
        await output_changes.aclose()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
