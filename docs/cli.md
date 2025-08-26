# CLI

This package includes a CLI which uses the library to interface with the Ness Serial Interface.

To use the CLI you must install it's dependencies by installing it with extras for `cli`:

```
pip install nessclient[cli]
ness-cli --help
```

## Events command

`ness-cli events` listens for events emitted by a connected alarm panel.

```sh
ness-cli events --host PANEL_HOST --port PORT
```

Pass `--interactive` to launch a terminal UI with live zone status and event logs.

### Logging raw packets

When troubleshooting or reporting issues it can be useful to capture the raw
ASCII packets exchanged with the panel. Provide a logfile to the `events`
command to record all transmitted (`TX`) and received (`RX`) packets:

```sh
ness-cli events --logfile packets.log
```

The option also works with the interactive UI:

```sh
ness-cli events --interactive --logfile packets.log
```

Include the generated file when raising an issue to help diagnose problems.
