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

Use `Client(host=..., port=...)` for an IP232 module or
`Client(serial_tty=...)` for a local serial port or registered serial proxy URL.
Serial connections use 9600 baud, 8N1 and no flow control. For a standalone
ESPHome proxy, install `serialx[esphome]`.

Call `await client.probe()` to wait for an arming status reply.
`PanelNotRespondingError` means the connection opened but the panel did not
answer in time. Run `keepalive()` to refresh state and reconnect, register
`on_availability_change` to receive communication updates, and call
`await client.close()` to release the port.

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
