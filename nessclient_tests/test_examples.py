"""Test the examples and the nessclient CLI tool."""

import asyncio
import logging

from examples import listening_for_events, sending_commands
from nessclient.cli.server import AlarmServer
from nessclient.event import PanelVersionUpdate

_LOGGER = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(threadName)-25s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def test_listening_for_events() -> None:
    """Test the listening_for_events.py example operation."""
    # Start an alarm-emulation server which will send events to the example
    server = AlarmServer(
        host=listening_for_events.host,
        port=listening_for_events.port,
        num_zones=32,
        panel_model=PanelVersionUpdate.Model.D32X,
        panel_major_version=1,
        panel_minor_version=1,
    )
    server._server.start(host=server._host, port=server._port)

    # Run the example for 5 seconds
    listening_for_events.main(timeout=5)

    # Shutdown
    server.stop()


def test_sending_commands() -> None:
    """Test the sending_commands.py example operation."""
    # Start an alarm-emulation server which will receive commands
    server = AlarmServer(
        host=sending_commands.host,
        port=sending_commands.port,
        num_zones=32,
        panel_model=PanelVersionUpdate.Model.D32X,
        panel_major_version=1,
        panel_minor_version=1,
    )

    server._server.start(host=server._host, port=server._port)
    server._start_simulation()

    # Run the example
    asyncio.run(sending_commands.main())

    # Shutdown
    server.stop()
