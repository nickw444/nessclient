import logging

import click
from importlib.metadata import version as importlib_version

from .events import events
from .send_command import send_command
from .server import server

LOG_LEVELS = ["error", "warning", "info", "debug"]

_LOGGER = logging.getLogger(__name__)


@click.group()
@click.option("--log-level", type=click.Choice(LOG_LEVELS), default="warning")
def cli(log_level: str) -> None:
    level = getattr(logging, log_level.upper())
    logging.basicConfig(level=level)
    _LOGGER.debug("nessclient version: %s", get_version())


@cli.command()
def version() -> None:
    """Print installed package version."""
    print(get_version())


def get_version() -> str:
    return importlib_version("nessclient")


cli.add_command(events)
cli.add_command(send_command)
cli.add_command(server)

if __name__ == "__main__":
    cli()
