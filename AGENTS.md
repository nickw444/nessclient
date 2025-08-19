# AI Agent Guidelines

This repository uses [uv](https://docs.astral.sh/uv/) for dependency management and task execution.

## Setup
- Install dependencies with `uv sync --dev`.

## Style, Linting, and Type Checking
- Format Python code with `uv run ruff format nessclient nessclient_tests`.
- Lint with `uv run ruff check nessclient nessclient_tests`.
- Run type checks using `uv run mypy --strict nessclient`.

## Testing
- Run the test suite with `uv run pytest`.

These commands should be executed and pass before committing any changes.
