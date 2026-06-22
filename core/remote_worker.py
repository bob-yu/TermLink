"""Remote serial worker proxy."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .login_state_machine import LoginConfig, LoginState, LoginStateMachine
from .serial_access_client import SerialAccessClient
from .serial_worker import WorkerState


@dataclass
class RemoteSerialConfig:
    """Remote serial connection configuration."""

    server_host: str
    server_port: int
    remote_port: str = ""
    name: str = "Remote"


class RemoteSerialWorkerProxy(QObject):
    """Proxy that exposes a remote serial port through the SerialWorker shape."""

    data_received = pyqtSignal(str)
    state_changed = pyqtSignal(WorkerState)
    login_state_changed = pyqtSignal(LoginState)
    error_occurred = pyqtSignal(str)
    keyword_detected = pyqtSignal(str, str)

    def __init__(self, network_client: SerialAccessClient, remote_port: str):
        super().__init__()
        self._network_client = network_client
        self._remote_port = remote_port
        self._state = (
            WorkerState.CONNECTED
            if network_client and network_client.is_connected
            else WorkerState.STOPPED
        )

        self._login_machine: Optional[LoginStateMachine] = None
        self._auto_login_enabled = False
        self._auto_commands: List[str] = []
        self._keywords: Dict[str, List[str]] = {}

        self.config = type(
            "Config",
            (),
            {
                "port": remote_port,
                "baudrate": 115200,
                "name": remote_port,
            },
        )()

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return (
            self._state == WorkerState.CONNECTED
            and self._network_client
            and self._network_client.is_connected
        )

    @property
    def log_filepath(self) -> str:
        return ""

    def setup_login(self, login_config: LoginConfig):
        """Set the optional automatic login configuration."""
        self._login_machine = LoginStateMachine(login_config)
        self._login_machine.set_send_callback(self.write)
        self._login_machine.set_state_change_callback(self._on_login_state_change)
        self._auto_login_enabled = True

    def set_auto_commands(self, commands: List[str]):
        """Set commands that should run after automatic login."""
        self._auto_commands = commands.copy()

    def set_keywords(self, keywords: Dict[str, List[str]]):
        """Set keyword detection rules."""
        self._keywords = keywords.copy()

    def set_auto_reconnect(self, enabled: bool, interval: float = 5):
        """Keep API compatibility; SerialAccessClient owns reconnect behavior."""
        pass

    def start(self):
        """Select the remote port and mark the proxy connected."""
        if self._network_client and self._network_client.is_connected:
            self._network_client.select_port(self._remote_port)
            self._state = WorkerState.CONNECTED
            self.state_changed.emit(self._state)
            return

        self._state = WorkerState.DISCONNECTED
        self.state_changed.emit(self._state)

    def stop(self):
        """Unselect the remote port and stop the proxy."""
        if self._network_client and self._network_client.is_connected:
            self._network_client.unselect_port(self._remote_port)
        self._state = WorkerState.STOPPED
        self.state_changed.emit(self._state)

    def write(self, data: str):
        """Send data to the remote serial port."""
        if not self._network_client or not self._network_client.is_connected:
            return
        self._network_client.send_to_port(self._remote_port, data)

    def send_command(self, command: str):
        """Send a command with a trailing newline."""
        if not command.endswith("\n"):
            command += "\n"
        self.write(command)

    def send_break(self):
        """Send a break request to the remote serial port."""
        if not self._network_client or not self._network_client.is_connected:
            return
        self._network_client.send_break(self._remote_port)

    def start_login(self):
        """Start the optional login flow."""
        if self._login_machine:
            self._login_machine.start()

    def feed_data(self, data: str):
        """Feed data received from the owning window/client."""
        self.data_received.emit(data)
        self._check_keywords(data)

        if self._auto_login_enabled and self._login_machine:
            self._login_machine.feed(data)

    def _on_login_state_change(self, state: LoginState):
        """Handle login state changes."""
        self.login_state_changed.emit(state)

        if state == LoginState.READY:
            self._execute_auto_commands()

    def _execute_auto_commands(self):
        """Run configured automatic commands."""
        for command in self._auto_commands:
            self.send_command(command)

    def _check_keywords(self, text: str):
        """Emit keyword detections for matching lines."""
        for keyword_type, keywords in self._keywords.items():
            for keyword in keywords:
                if keyword in text:
                    for line in text.split("\n"):
                        if keyword in line:
                            self.keyword_detected.emit(keyword_type, line.strip())

    @staticmethod
    def list_ports() -> List[str]:
        """Remote mode does not enumerate local serial ports."""
        return []
