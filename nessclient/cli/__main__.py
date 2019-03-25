import logging

import click
import pkg_resources

from .events import events
from .send_command import send_command
from .server import server

LOG_LEVELS = ['error', 'warning', 'info', 'debug']

_LOGGER = logging.getLogger(__name__)


@click.group()
@click.option('--log-level', type=click.Choice(LOG_LEVELS), default='warning')
def cli(log_level: str):
    level = getattr(logging, log_level.upper())
    logging.basicConfig(level=level)
    _LOGGER.debug('nessclient version: %s', get_version())


@cli.command()
def version():
    """Print installed package version."""
    print(get_version())


def get_version():
    return pkg_resources.get_distribution('nessclient').version


cli.add_command(events)
cli.add_command(send_command)
cli.add_command(server)

if __name__ == '__main__':
    cli()
