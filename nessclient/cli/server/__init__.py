import click

from .alarm_server import AlarmServer
from ...event import PanelVersionUpdate

DEFAULT_PORT = 65432


@click.command(help="Run a dummy server")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=DEFAULT_PORT)
@click.option(
    "--zones",
    type=click.IntRange(1, 32),
    default=16,
    help="Number of zones to simulate (1-32)",
)
@click.option(
    "--panel-model",
    type=click.Choice([m.name for m in PanelVersionUpdate.Model]),
    default=PanelVersionUpdate.Model.D8X.name,
)
@click.option("--panel-version", default="0.0")
def server(
    host: str, port: int, zones: int, panel_model: str, panel_version: str
) -> None:
    major_str, minor_str = panel_version.split(".")
    s = AlarmServer(
        host=host,
        port=port,
        num_zones=zones,
        panel_model=PanelVersionUpdate.Model[panel_model],
        panel_major_version=int(major_str),
        panel_minor_version=int(minor_str),
    )
    s.start()
