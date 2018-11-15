import logging

import click

from .events import events
from .send_command import send_command
from .server import server

LOG_LEVELS = ['error', 'warning', 'info', 'debug']


@click.group()
@click.option('--log-level', type=click.Choice(LOG_LEVELS), default='warning')
def cli(log_level: str):
    level = getattr(logging, log_level.upper())
    logging.basicConfig(level=level)


cli.add_command(events)
cli.add_command(send_command)
cli.add_command(server)

if __name__ == '__main__':
    cli()
