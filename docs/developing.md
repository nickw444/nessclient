# Developing
Use [uv](https://docs.astral.sh/uv/) to set up the local environment:

```sh
uv sync --dev
```

## Running tests

```sh
uv run pytest
```

## Linting

```sh
uv run black nessclient nessclient_tests
uv run flake8 nessclient nessclient_tests
```

## Type Checking

```sh
uv run mypy --strict nessclient
```
