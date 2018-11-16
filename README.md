# nessclient

[![](https://travis-ci.org/nickw444/nessclient.svg?branch=master)](https://travis-ci.org/nickw444/nessclient)
[![](https://coveralls.io/repos/nickw444/nessclient/badge.svg)](https://coveralls.io/r/nickw444/nessclient)
[![](https://img.shields.io/pypi/v/nessclient.svg)](https://pypi.python.org/pypi/nessclient/)

A python implementation/abstraction of the [Ness D8x / D16x Serial Interface ASCII protocol](http://www.nesscorporation.com/Software/Ness_D8-D16_ASCII_protocol.pdf)

## Installing nessclient

`nessclient` is available directly from pip:

```sh
pip install nessclient
```

## CLI

This package includes a CLI which uses the library to interface with the Ness Serial Interface. You can read more in [the docs]()

To use the CLI you must install it's dependencies by installing it with extras for `cli`: 

```
pip install nessclient[cli]
ness-cli --help
``` 

## API Documentation
You can find the full API documentation [here]()

## Examples

Please see [Examples]() section in the docs for examples. These same examples can be found as source in the [examples/](examples) directory. 
 
## Developing

Please see [Developing]() section in the docs for development environment setup information.
