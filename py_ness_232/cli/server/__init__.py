import click

from .alarm_server import AlarmServer


@click.command(help="Run a dummy server")
@click.option('--host', default='127.0.0.1')
@click.option('--port', default=65432)
def server(host, port):
    s = AlarmServer(host=host, port=port)
    s.start()
