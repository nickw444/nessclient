# nessclient

[![](https://travis-ci.org/nickw444/nessclient.svg?branch=master)](https://travis-ci.org/nickw444/nessclient)
[![](https://coveralls.io/repos/nickw444/nessclient/badge.svg)](https://coveralls.io/r/nickw444/nessclient)
[![](https://img.shields.io/pypi/v/nessclient.svg)](https://pypi.python.org/pypi/nessclient/)
[![](https://readthedocs.org/projects/nessclient/badge/?version=latest&style=flat)](https://nessclient.readthedocs.io/en/latest/)

A python implementation/abstraction of the [Ness D8x / D16x Serial Interface ASCII protocol](http://www.nesscorporation.com/Software/Ness_D8-D16_ASCII_protocol.pdf)

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

## Connecting

Starting with nessclient 1.4.0, `serial_tty` supports serial proxies and
`Client.probe()` checks communication with the panel.

`Client` connects either to an IP232 module or directly to the panel's serial
interface. The serial interface always runs at 9600 baud, 8 data bits, no
parity, one stop bit and no flow control; the library applies these settings.

```python
# IP232 module
client = Client(host="192.168.1.50", port=2401)

# Local serial port, or any port or URL supported by serialx
client = Client(serial_tty="/dev/ttyUSB0")
client = Client(serial_tty="COM3")
```

Serial ports are opened with [serialx](https://github.com/puddly/serialx), so
`serial_tty` accepts its URLs as well as local paths, including serial proxy
URLs provided by Home Assistant. Using ESPHome serial proxy URLs outside Home
Assistant requires `pip install 'serialx[esphome]'`.

Call `await client.probe()` to confirm that the panel itself is answering. It
opens the connection, starts processing responses and waits for a valid reply to
an arming status request. It raises `PanelNotRespondingError` when the
connection opens but the panel does not reply in time, and `OSError` (or
`serialx.SerialException`) when the connection cannot be opened. Keep the
client running with `keepalive()` afterwards, or release it with `close()`.

While `keepalive()` runs, the client reconnects with bounded backoff, refreshes
state after every reconnection and periodically confirms that the panel answers
status requests. Register `on_availability_change` to be told when communication
with the panel is lost or restored. `close()` stops all background work and
releases the connection, and can be called more than once.

nessclient requires Python 3.11 or newer.

```{toctree}
:maxdepth: 2
:caption: Contents:

cli.md
api.rst
examples.md
developing.md
```

# Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
