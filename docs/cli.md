# CLI

This package includes a CLI which uses the library to interface with the Ness Serial Interface.

To use the CLI you must install it's dependencies by installing it with extras for `cli`:

```
pip install nessclient[cli]
ness-cli --help
```

## Events command

`ness-cli events` listens for events emitted by a connected alarm panel and
displays a terminal UI with live zone status and event logs.

```sh
ness-cli events --host PANEL_HOST --port PORT
```

### Logging raw packets

When troubleshooting or reporting issues it can be useful to capture the raw
ASCII packets exchanged with the panel. Provide a logfile to the `events`
command to record all transmitted (`TX`) and received (`RX`) packets:

```sh
ness-cli events --logfile packets.log
```

Include the generated file when raising an issue to help diagnose problems.

### Checksum validation

Packet checksums can be validated to drop malformed messages. Pass
`--validate-checksum` to the `events` command to enable verification:

```sh
ness-cli events --host PANEL_HOST --port PORT --validate-checksum
```

The same flag is available on the `server` command to verify incoming
packets from clients.
