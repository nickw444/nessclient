import click

from .alarm_server import AlarmServer
from ...event import PanelVersionUpdate

DEFAULT_PORT = 65432


@click.command(help="Run a dummy server")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=DEFAULT_PORT)
@click.option(
    "--panel-model",
    type=click.Choice(
        [m.name for m in PanelVersionUpdate.Model], case_sensitive=False
    ),
    default=PanelVersionUpdate.Model.D8X.name,
)
@click.option("--panel-version", default="5.8")
def server(host: str, port: int, panel_model: str, panel_version: str) -> None:
    model = PanelVersionUpdate.Model[panel_model.upper()]
    major_str, minor_str = panel_version.split(".")
    s = AlarmServer(
        host=host,
        port=port,
        panel_model=model,
        panel_major=int(major_str),
        panel_minor=int(minor_str),
    )
    s.start()
