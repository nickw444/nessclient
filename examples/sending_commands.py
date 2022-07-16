import asyncio

from nessclient import Client

loop = asyncio.get_event_loop()
host = '127.0.0.1'
port = 65432
client = Client(host=host, port=port)

# Send arming command via library abstraction
loop.run_until_complete(client.arm_away('1234'))
# Send panic command via library abstraction
loop.run_until_complete(client.panic('1234'))
# Send disarm command via library abstraction
loop.run_until_complete(client.disarm('1234'))
# Send aux control command for output 2 via library abstraction
loop.run_until_complete(client.aux(2))
# Send custom command
# In this instance, we are sending a status update command to view
# output status
loop.run_until_complete(client.send_command('S15'))

client.close()
loop.close()
