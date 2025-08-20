# Developing
Use [uv](https://docs.astral.sh/uv/) to set up the local environment and
install optional extras such as the CLI tools:

```sh
uv sync --dev --all-extras
```

## Running tests

```sh
uv run pytest
```

## Linting

```sh
uv run ruff format nessclient nessclient_tests
uv run ruff check nessclient nessclient_tests
```

## Type Checking

```sh
uv run mypy --strict nessclient
```
