import asyncio
import contextlib

from nessclient import Client


async def main() -> None:
    host = "127.0.0.1"
    port = 65432
    client = Client(host=host, port=port)
    # Run background loops so responses are received while awaiting
    keepalive_task = asyncio.create_task(client.keepalive())
    try:
        # Send arming command via library abstraction
        await client.arm_away("1234")
        # Send panic command via library abstraction
        await client.panic("1234")
        # Send disarm command via library abstraction
        await client.disarm("1234")
        # Send aux control command for output 2 via library abstraction
        await client.aux(2)
        # Send custom command
        # In this instance, we are sending a status update command to view
        # output status
        await client.send_command("S15")
        # Send and await a status request to receive the decoded response
        # note: the background keepalive must be running for this to work
        resp = await client.send_command_and_wait("S14", timeout=5.0)
        print("Arming status response:", resp)
    finally:
        await client.close()
        keepalive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await keepalive_task


if __name__ == "__main__":
    asyncio.run(main())
