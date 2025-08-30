import asyncio

from nessclient import Client


async def main() -> None:
    client = Client(host="127.0.0.1", port=65432)
    events = client.events()
    state_changes = client.state_changes()
    zone_changes = client.zone_changes()
    output_changes = client.aux_output_changes()

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

    try:
        await asyncio.gather(
            client.keepalive(),
            print_events(),
            print_state_changes(),
            print_zone_changes(),
            print_output_changes(),
        )
    finally:
        await events.aclose()
        await state_changes.aclose()
        await zone_changes.aclose()
        await output_changes.aclose()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
