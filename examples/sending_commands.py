import asyncio
from nessclient import Client

async def main():
    host = '127.0.0.1'
    port = 4999

    print(f"Connecting to {host}:{port}")

    try:
        client = Client(host=host, port=port)

        if hasattr(client, 'connect'):
            await client.connect()

        await client.arm_away('123')

        await asyncio.sleep(1)

        await client.panic('123')

        await asyncio.sleep(1)

        await client.disarm('123')

        await asyncio.sleep(1)

        await client.aux(2)

        await asyncio.sleep(1)

        await client.send_command('S15')
    finally:
        try:
            await client.close()
        except Exception as e:
            print(f"Error closing client: {e}")


if __name__ == "__main__":
    print("Starting script...")
    asyncio.run(main())
    print("Script finished")