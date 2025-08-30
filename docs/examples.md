# Examples

## Sending Commands
A list of commands that can be sent can be found in the _Input Commands_ section of the [protocol documentation](http://www.nesscorporation.com/Software/Ness_D8-D16_ASCII_protocol.pdf). Additional information on the user-level commands available can be found in the _Operation Summary_ of the [installer manual](http://nesscorporation.com/InstallationManual/D8xD16x_installer_manual_rev7.7.pdf).

```{literalinclude} ../examples/sending_commands.py
:language: python
```

## Listening for Events

```{literalinclude} ../examples/listening_for_events.py
:language: python
```

## Streaming Events

The `nessclient` API also exposes asynchronous streams as an alternative to
callbacks. Instead of registering handlers, you can iterate over
`client.events()`, `client.state_changes()` and `client.zone_changes()`.
This approach fits naturally into `asyncio` applications and allows
cooperative scheduling via `await`.

```{literalinclude} ../examples/streaming_events.py
:language: python
```
