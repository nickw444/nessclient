"""End-to-end tests using client and alarm-emulator-server."""

import asyncio
import logging
import threading
import time
import unittest
from collections.abc import Callable
from typing import cast

import pytest

from nessclient import ArmingMode, ArmingState, BaseEvent, Client
from nessclient.cli.server import AlarmServer
from nessclient.cli.server.alarm import Alarm
from nessclient.cli.server.zone import Zone
from nessclient.event import PanelVersionUpdate, StatusUpdate

localhost = "127.0.0.1"


_LOGGER = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(threadName)-25s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class ClientServerPair:
    """
    Provides a nessclient Client connected to a test alarm emulator.

    Facilitates end-to-end tests
    """

    test_port = 65433  # Different from the default CLI server port

    server: AlarmServer
    client: Client
    loop: asyncio.AbstractEventLoop
    loop_thread: threading.Thread
    keep_alive_task: asyncio.Task[None]
    keepalive_thread: threading.Thread

    def __init__(  # noqa: PLR0913 # Not worth reducing arg count for test
        self,
        zone_change_callback: Callable[[int, bool], None] | None = None,
        state_change_callback: (
            Callable[[ArmingState, ArmingMode | None], None] | None
        ) = None,
        event_received_callback: Callable[[BaseEvent], None] | None = None,
        server_host: str = localhost,
        client_host: str = localhost,
        server_port: int = test_port,
        client_port: int = test_port,
    ) -> None:
        """Create a ness Client and emulated-alarm server pair."""
        _LOGGER.info("ClientServerPair init")

        self.server = AlarmServer(
            host=server_host,
            port=server_port,
            num_zones=32,
            panel_model=PanelVersionUpdate.Model.D32X,
            panel_major_version=1,
            panel_minor_version=1,
        )
        self.client = Client(host=client_host, port=client_port, update_interval=1)

        self.client.on_zone_change(zone_change_callback)
        self.client.on_state_change(state_change_callback)
        self.client.on_event_received(event_received_callback)

        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(
            target=lambda: self.loop.run_forever(), name="asyncio event loop"
        )
        self.loop_thread.start()

    def run(self, *, do_keepalive: bool = True, do_server: bool = True) -> None:
        """Start the Client + emulated-alarm."""
        if do_server:
            self.start_server()

        if do_keepalive:
            time.sleep(0.05)
            self.start_keepalive()

    def start_server(self) -> None:
        """Start the emulated alarm server."""
        self.server._server.start(host=self.server._host, port=self.server._port)

    def start_keepalive(self) -> None:
        """Start the keep-alive task of the client."""

        def _do_keepalive() -> None:
            """Thread function to run the Client keep-alive task."""

            async def _keepalive_task() -> None:
                """Async task for he keep-alive task."""
                _LOGGER.info("keepalive_task started")
                try:
                    self.keep_alive_task = self.loop.create_task(
                        self.client.keepalive(), name="keepalive_task"
                    )
                    await self.keep_alive_task

                except asyncio.CancelledError:
                    # this happens when stopping
                    _LOGGER.info("do_keepalive cancelled")

            _LOGGER.info("do_keepalive start")
            asyncio.run_coroutine_threadsafe(_keepalive_task(), self.loop).result()

        self.keepalive_thread = threading.Thread(
            target=_do_keepalive, name="client keep-alive"
        )
        self.keepalive_thread.start()

    def stop_keepalive(self) -> None:
        """Stop the keep-alive task of the client."""

        async def _cancel() -> None:
            """Cancel keep-alive and close client."""
            _LOGGER.info("cancel keep-alive thread")
            self.keep_alive_task.cancel()
            _LOGGER.info("close client")
            await self.client.close()

        asyncio.run_coroutine_threadsafe(_cancel(), self.loop).result()
        self.keepalive_thread.join()

    def stop_server(self) -> None:
        """Stop the emulated alarm server."""
        _LOGGER.info("stop server")
        self.server.stop()

    def stop(self) -> None:
        """Stop and close the Client + emulated-alarm server."""
        self.stop_keepalive()
        self.stop_server()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join()
        self.loop.close()
        _LOGGER.info("Pair stopped")


class ClientServerConnectionTests(unittest.TestCase):
    """End-to-end tests using client and alarm-emulator-server."""

    zone_changes: int = 0
    state_changes: int = 0
    events_recieved: int = 0

    def setup_client_server(self) -> ClientServerPair:
        """Start a client + alarm-emulator server pair."""

        def _count_events_received(event: BaseEvent) -> None:
            """Event Received callback that counts calls to it."""
            _LOGGER.info(event)
            self.events_recieved += 1

        def _count_state_change(
            state: ArmingState, arming_mode: ArmingMode | None
        ) -> None:
            """State change callback that counts calls to it."""
            _LOGGER.info("Alarm state changed to %s (mode: %s)", state, arming_mode)
            self.state_changes += 1

        # Ruff: Bool part of Pre-defined API
        def _count_zone_change(zone: int, triggered: bool) -> None:  # noqa: FBT001
            """Zone change callback that counts calls to it."""
            _LOGGER.info("Zone %s changed to %s", zone, triggered)
            self.zone_changes += 1

        _LOGGER.info("Exercise Connection Test")
        pair = ClientServerPair(
            zone_change_callback=_count_zone_change,
            state_change_callback=_count_state_change,
            event_received_callback=_count_events_received,
        )

        pair.run()
        time.sleep(1)
        assert pair.client.connected_count == 1

        return pair

    def shutdown_client_server(self, pair: ClientServerPair) -> None:
        """Shutdown a client + alarm-emulator server pair."""
        pair.stop()
        _LOGGER.info("Basic Connection Test Complete")

    def test_basic_connection(self) -> None:
        """Check that a connection can be established."""
        _LOGGER.info("Basic Connection Test")
        pair = self.setup_client_server()
        self.shutdown_client_server(pair)
        _LOGGER.info("Basic Connection Test Complete")

    def test_bad_packet(self) -> None:
        """Check that a bad packet doesn't cause a crash."""
        pair = self.setup_client_server()
        pair.server._server._write_to_all_clients("\xf5\xf5\xf5\xf5")
        self.shutdown_client_server(pair)

    def test_zone_update(self) -> None:
        """Exercise zone update function get_zone_state_event_type()."""
        pair = self.setup_client_server()
        time.sleep(1)
        self.zone_changes = 0

        pair.server._alarm.update_zone(5, Zone.State.UNSEALED)
        time.sleep(1)
        pair.server._alarm.update_zone(5, Zone.State.SEALED)
        time.sleep(1)
        self.shutdown_client_server(pair)
        assert self.zone_changes == 2  # noqa: PLR2004

    def test_bad_zone_update(self) -> None:
        """Exercise zone update function get_zone_state_event_type()."""
        self.zone_changes = 0
        pair = self.setup_client_server()
        with pytest.raises(NotImplementedError):
            pair.server._alarm.update_zone(5, cast("Zone.State", 5))
        self.shutdown_client_server(pair)
        assert self.zone_changes == 0

    def test_status_request(self) -> None:
        """Exercise send_command for zone status request."""
        self.events_recieved = 0
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            await pair.client.send_command("S00")
            await asyncio.sleep(0.5)
            assert self.events_recieved > 1

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_wait_reply(self) -> None:
        """Test waiting for status update response."""
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            event = await pair.client.send_command_and_wait("S00")
            _LOGGER.debug("Waited for %s", event)
            assert event is not None
            assert event.request_id == StatusUpdate.RequestID.ZONE_1_16_INPUT_UNSEALED

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_wait_reply_timeout(self) -> None:
        """
        Test waiting for cbus update response - this should timeout.

        Timeout because server does not handle this request
        """
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            event = await pair.client.send_command_and_wait("S02")
            assert event is None

        with pytest.raises(asyncio.TimeoutError):
            asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_arm_away_trip_disarm(self) -> None:
        """
        Test sequence of Arm-away, Trip, Disarm causes correct alarm-emulator states.

        Arm-Away - initially goes to EXIT_DELAY state, then to ARMED_AWAY
        Trip - (for instant-trip zone) goes to TRIPPED
        Disarm - goes to DISARMED
        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2

        async def _do_async_test() -> None:
            _LOGGER.debug("arming away")
            await pair.client.arm_away("1234")
            await asyncio.sleep(1)
            assert pair.server._alarm.state == Alarm.ArmingState.EXIT_DELAY
            # wait for exit delay to finish
            await asyncio.sleep(2)
            await pair.client.send_command("S00")
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
            assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_AWAY

            # Check the Client.trip() method can trigger the alarm immediately
            # to TRIPPED state. (i.e. without an entry-delay)
            pair.server._alarm.trip(delay=False)
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.TRIPPED

            # Check the Client.disarm() method when in a tripped state sets the
            # alarm to DISARMED state
            _LOGGER.debug("disarming")
            await pair.client.disarm("1234")
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.DISARMED

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_arm_home_trip_duress(self) -> None:
        """
        Test sequence of Arm-home, Trip, Duress causes correct alarm-emulator states.

        Arm-Home - initially goes to EXIT_DELAY state, then to ARMED_HOME
        Trip - (for delayed-trip zone) goes to ENTRY_DELAY then TRIPPED
        Disarm with duress code - goes to DURESS
        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2
        pair.server._alarm.entry_delay = 2

        async def _do_async_test() -> None:
            # Test Client.arm_away() call causes alarm-emulator to initially
            # go to EXIT_DELAY state, then to ARMED_HOME
            _LOGGER.debug("arming home")
            await pair.client.arm_home("1234")
            await asyncio.sleep(1)
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.EXIT_DELAY
            # wait for exit delay to finish
            await asyncio.sleep(2)
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
            assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_HOME

            # Check the Client.trip() method can trigger the alarm, initially to
            # an ENTRY_DELAY state, then to TRIPPED state
            pair.server._alarm.trip()
            await asyncio.sleep(1)
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.ENTRY_DELAY
            # wait for entry delay to finish
            await asyncio.sleep(2)
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.TRIPPED

            # Check a 'duress' prefix whilst disarming sets the alarm
            # to DURESS state
            _LOGGER.debug("disarming under duress")
            await pair.client.send_command("51234E")
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.get_state() == Alarm.ArmingState.DURESS

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_aux(self) -> None:
        """Test AUX control commands."""
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            # Check that AUX on / off set the alarm auxilliary outputs
            _LOGGER.debug("aux on")
            await pair.client.aux_output(1, state=True)
            await asyncio.sleep(0.5)
            _LOGGER.debug("pair.server._alarm.aux = %s", pair.server._alarm.aux_outputs)
            assert pair.server._alarm.aux_outputs[0].bool_state()
            _LOGGER.debug("aux off")
            await pair.client.aux_output(1, state=False)
            await asyncio.sleep(0.5)
            _LOGGER.debug("pair.server._alarm.aux = %s", pair.server._alarm.aux_outputs)
            assert not pair.server._alarm.aux_outputs[0].bool_state()

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_panic(self) -> None:
        """Check the Client.panic() method sets the alarm to PANIC state."""
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            _LOGGER.debug("panic")
            await pair.client.panic("1234")
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.state == Alarm.ArmingState.PANIC

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_medical(self) -> None:
        """Check the 'medical' code sets the alarm to MEDICAL state."""
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            _LOGGER.debug("Medical")
            await pair.client.send_command("2E")
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.state == Alarm.ArmingState.MEDICAL

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    def test_fire(self) -> None:
        """Check the 'fire' code sets the alarm to FIRE state."""
        pair = self.setup_client_server()

        async def _do_async_test() -> None:
            _LOGGER.debug("Fire")
            await pair.client.send_command("3E")
            await pair.client.send_command_and_wait("S14")
            assert pair.server._alarm.state == Alarm.ArmingState.FIRE

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()
        self.shutdown_client_server(pair)

    ####################################################################
    # Test that the emulated-alarm server interactive CLI works properly

    def test_server_arm_disarm_commands(self) -> None:
        """
        Test the emulated-alarm server CLI 'Arm' & 'Diarm' commands.

        Arm the alarm from the emulated-alarm server console
        Check that it goes initially to EXIT_DELAY state
        Then to the ARMED_AWAY

        Disarm the alarm from the emulated-alarm server console
        Check that it goes to DISARMED state
        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2
        pair.server._execute_command("A")
        time.sleep(1)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.EXIT_DELAY
        # wait for exit delay to finish
        time.sleep(2)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
        assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_AWAY

        pair.server._execute_command("D")
        time.sleep(0.5)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.DISARMED

        self.shutdown_client_server(pair)

    def test_server_arm_home_command(self) -> None:
        """
        Test the emulated-alarm server CLI 'Arm-Home' command.

        Arm-Home the alarm from the emulated-alarm server console
        Check that it goes initially to EXIT_DELAY state
        Then to the ARMED_HOME
        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2

        pair.server._execute_command("AH")
        time.sleep(1)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.EXIT_DELAY
        # wait for exit delay to finish
        time.sleep(2)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
        assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_HOME

        self.shutdown_client_server(pair)

    def test_server_arm_day_command(self) -> None:
        """
        Test the emulated-alarm server CLI 'Arm-Day' command.

        Arm-Day the alarm from the emulated-alarm server console
        Check that it goes initially to EXIT_DELAY state
        Then to the ARMED_DAY
        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2

        pair.server._execute_command("AD")
        time.sleep(1)
        assert pair.server._alarm.state == Alarm.ArmingState.EXIT_DELAY
        # wait for exit delay to finish
        time.sleep(2)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
        assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_DAY

        self.shutdown_client_server(pair)

    def test_server_arm_night_command(self) -> None:
        """
        Test the emulated-alarm server CLI 'Arm-Night' command.

        Arm-Night the alarm from the emulated-alarm server console
        Check that it goes initially to EXIT_DELAY state
        Then to the ARMED_NIGHT
        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2

        pair.server._execute_command("AN")
        time.sleep(1)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.EXIT_DELAY
        # wait for exit delay to finish
        time.sleep(2)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
        assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_NIGHT

        self.shutdown_client_server(pair)

    def test_server_arm_vacation_trip_commands(self) -> None:
        """
        Test the emulated-alarm server CLI 'Arm-Vacation' & 'Trip' commands.

        Arm-Vacation the alarm from the emulated-alarm server console
        Check that it goes initially to EXIT_DELAY state
        Then to the ARMED_VACATION

        """
        pair = self.setup_client_server()
        pair.server._alarm.exit_delay = 2
        pair.server._alarm.entry_delay = 2

        pair.server._execute_command("AV")
        time.sleep(1)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.EXIT_DELAY
        # wait for exit delay to finish
        time.sleep(2)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.ARMED
        assert pair.server._alarm.get_arming_mode() == Alarm.ArmingMode.ARMED_VACATION

        # Trip the alarm from the emulated-alarm server console
        # Check that it goes initially to ENTRY_DELAY state
        # Then to the TRIPPED
        pair.server._execute_command("T")
        time.sleep(1)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.ENTRY_DELAY
        # wait for exit delay to finish
        time.sleep(2)
        assert pair.server._alarm.get_state() == Alarm.ArmingState.TRIPPED

        self.shutdown_client_server(pair)

    def test_activity_simulation_command(self) -> None:
        """
        Test the emulated-alarm server CLI activity simulation command.

        Enable zone-activity simulation for the
        alarm from the emulated-alarm server console
        Check activity was detected

        Disable zone-activity simulation for the
        alarm from the emulated-alarm server console
        Check no activity was detected
        """
        pair = self.setup_client_server()

        self.zone_changes = 0
        pair.server._execute_command("S")
        time.sleep(5.5)
        assert self.zone_changes > 0

        self.zone_changes = 0
        pair.server._execute_command("S")
        time.sleep(5.5)
        assert self.zone_changes == 0

        self.shutdown_client_server(pair)

    def test_quit_command(self) -> None:
        """
        Test the emulated-alarm server CLI Quit command.

        Quit the emulated-alarm server console
        Causes the emulated-alarm to stop and close
        """
        pair = self.setup_client_server()

        pair.server._execute_command("Q")

        time.sleep(0.5)

        self.shutdown_client_server(pair)

    def test_refused_connection(self) -> None:
        """Check a connection refused error doesn't cause crashes."""
        _LOGGER.info("Connection Refused Test")
        pair = ClientServerPair(
            client_port=ClientServerPair.test_port + 1
        )  # ensure connection refused
        pair.run()
        time.sleep(5)
        assert pair.client.connected_count == 0
        pair.stop()
        _LOGGER.info("Connection Refused Test Complete")

    def test_disconnect_connection(self) -> None:
        """Check a transport disconnection can be reconnected."""
        _LOGGER.info("Disconnection Test")
        pair = self.setup_client_server()
        time.sleep(1)
        pair.server._server.disconnect_all_clients()
        time.sleep(1)

        # Send a status request and await the reply
        async def _do_async_test() -> None:
            event = await pair.client.send_command_and_wait("S00")
            _LOGGER.debug("Waited for %s", event)
            assert event is not None
            assert event.request_id == StatusUpdate.RequestID.ZONE_1_16_INPUT_UNSEALED

        asyncio.run_coroutine_threadsafe(_do_async_test(), pair.loop).result()

        assert pair.client.disconnection_count == 1

        self.shutdown_client_server(pair)
        _LOGGER.info("Disconnection Test Complete")
