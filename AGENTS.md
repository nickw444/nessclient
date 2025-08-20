# AI Agent Guidelines

This repository uses [uv](https://docs.astral.sh/uv/) for dependency management and task execution.

## Protocol Documentation
- Refer to [`D8-32X Serial Protocol Public.md`](./D8-32X%20Serial%20Protocol%20Public.md) for details on the device protocol.

## Setup
- Install dependencies with `uv sync --dev --all-extras`.

## Style, Linting, and Type Checking
- Format Python code with `uv run ruff format .`.
- Lint with `uv run ruff check .`.
- Run type checks using `uv run mypy --strict nessclient`.

## Testing
- Run the test suite with `uv run pytest`.

These commands should be executed and pass before committing any changes.
