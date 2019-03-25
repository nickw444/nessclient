# nessclient

[![](https://travis-ci.org/nickw444/nessclient.svg?branch=master)](https://travis-ci.org/nickw444/nessclient)
[![codecov](https://codecov.io/gh/nickw444/nessclient/branch/master/graph/badge.svg)](https://codecov.io/gh/nickw444/nessclient)
[![](https://img.shields.io/pypi/v/nessclient.svg)](https://pypi.python.org/pypi/nessclient/)
[![](https://readthedocs.org/projects/nessclient/badge/?version=latest&style=flat)](https://nessclient.readthedocs.io/en/latest/)

A python implementation/abstraction of the [Ness D8x / D16x Serial Interface ASCII protocol](http://www.nesscorporation.com/Software/Ness_D8-D16_ASCII_protocol_rev13.pdf)

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

## API Documentation
You can find the full API documentation [here](https://nessclient.readthedocs.io/en/latest/api.html)

## Examples

Please see [Examples](https://nessclient.readthedocs.io/en/latest/examples.html) section in the docs for examples. These same examples can be found as source in the [examples/](examples) directory. 
 
## Developing

Please see [Developing](https://nessclient.readthedocs.io/en/latest/developing.html) section in the docs for development environment setup information.
