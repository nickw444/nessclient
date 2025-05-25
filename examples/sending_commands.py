import asyncio
from nessclient import Client


async def main():
    host = '172.0.0.1'
    port = 4999
    client = Client(host=host, port=port)

    # Send arming command via library abstraction
    await client.arm_away('1234')
    # Send panic command via library abstraction
    await client.panic('1234')
    # Send disarm command via library abstraction
    await client.disarm('1234')
    # Send aux control command for output 2 via library abstraction
    await client.aux(2)
    # Send custom command
    # In this instance, we are sending a status update command to view
    # output status
    await client.send_command('S15')

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
