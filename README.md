# nessclient

[![](https://travis-ci.org/nickw444/nessclient.svg?branch=master)](https://travis-ci.org/nickw444/nessclient)
[![codecov](https://codecov.io/gh/nickw444/nessclient/branch/master/graph/badge.svg)](https://codecov.io/gh/nickw444/nessclient)
[![](https://img.shields.io/pypi/v/nessclient.svg)](https://pypi.python.org/pypi/nessclient/)
[![](https://readthedocs.org/projects/nessclient/badge/?version=latest&style=flat)](https://nessclient.readthedocs.io/en/latest/)


A python implementation/abstraction of the [Ness D8x / D16x Serial Interface ASCII protocol](./D8-32X%20Serial%20Protocol%20Public.pdf)

## Supported Models

- D8X
- D8X_CEL_3G
- D8X_CEL_4G
- D16X
- D16X_CEL_3G
- D16X_CEL_4G
- D32X
- DPLUS8

## Installing nessclient

`nessclient` is available directly from pip:

```sh
pip install nessclient
```

## Documentation

The full documentation can be found at [Read the Docs](https://nessclient.readthedocs.io/en/latest/)

## CLI

This package includes a CLI which uses the library to interface with the Ness Serial Interface. You can read more in [the docs](https://nessclient.readthedocs.io/en/latest/cli.html)

To use the CLI you must install it's dependencies by installing it with extras for `cli`:

```
pip install nessclient[cli]
ness-cli --help
```

The CLI exposes several high level commands:

- `events` – listen for alarm events emitted by a connected panel. Use `--interactive` for a terminal UI with live zone status and event logs.
- `send` – send a raw command to the panel.
- `server` – run a dummy panel server, useful for local development when an alarm panel isn't available.
- `version` – print the installed package version.

Run `ness-cli COMMAND --help` for full options on each command.

#### Server zones

The dummy server can simulate a configurable number of zones independent of the panel model. Use `--zones` to set the count (1–32):

```
ness-cli server --zones 24 --panel-model D8X --panel-version 8.7
```

- `S00` status includes unsealed zones in 1–16 (or fewer if the configured count is < 16).
- `S20` always responds: it returns an empty set when the configured count is ≤ 16; otherwise it reports unsealed zones in 17–N.

### Capturing raw packets

When reporting issues it can be helpful to provide the raw ASCII packets
exchanged with the panel. The `events` command accepts a `--logfile` option that
records each transmitted (`TX`) and received (`RX`) packet:

```sh
ness-cli events --logfile packets.log
```

This works in both normal and `--interactive` modes. Include the generated log
file with bug reports to assist with troubleshooting.

## API Documentation
You can find the full API documentation [here](https://nessclient.readthedocs.io/en/latest/api.html)

## Examples

Please see [Examples](https://nessclient.readthedocs.io/en/latest/examples.html) section in the docs for examples. These same examples can be found as source in the [examples/](examples) directory. 
 
## Developing

For a quick development setup, install dependencies and tooling with [uv](https://docs.astral.sh/uv/):

```
uv sync --dev --all-extras
```

Before submitting changes, ensure code is formatted, linted, type-checked and tested:

```
uv run ruff format .
uv run ruff check .
uv run mypy --strict nessclient
uv run pytest
```

See the [Developing](https://nessclient.readthedocs.io/en/latest/developing.html) section in the docs for more details on contributing and environment setup.
