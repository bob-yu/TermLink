from dataclasses import dataclass, field
from typing import Dict, List


DEFAULT_REMOTE_SERIAL_PORT = 56337


@dataclass
class LoginConfigData:
    username: str = "root"
    password: str = "root"
    login_prompt: str = "login:"
    password_prompt: str = "Password:"
    shell_prompt: List[str] = field(default_factory=lambda: ["#", "$"])


@dataclass
class PortConfigData:
    name: str = ""
    port: str = ""
    baudrate: int = 115200
    data_bits: int = 8
    parity: str = "N"
    stop_bits: float = 1.0
    flow_control: str = "none"
    login: LoginConfigData = field(default_factory=LoginConfigData)
    auto_commands: List[str] = field(default_factory=list)
    keywords: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CommandSetData:
    name: str = ""
    commands: List[str] = field(default_factory=list)


@dataclass
class HighlightRuleData:
    name: str = ""
    pattern: str = ""
    color: str = "#fff3cd"
    case_sensitive: bool = False
    regex: bool = False
    enabled: bool = True


@dataclass
class AppConfigData:
    serial_ports: List[PortConfigData] = field(default_factory=list)
    log_dir: str = "logs"
    auto_reconnect: bool = True
    reconnect_interval: int = 5
    scan_patterns: List[str] = field(default_factory=lambda: ["/dev/ttyUSB*", "/dev/ttyACM*"])
    serial_access_mode: str = "disabled"
    serial_access_host: str = "0.0.0.0"
    serial_access_port: int = DEFAULT_REMOTE_SERIAL_PORT
    serial_access_server_address: str = ""
    scrollback_lines: int = 5000
    terminal_font_family: str = ""
    terminal_font_size: int = 11
    log_enabled: bool = True
    log_timestamp: bool = True
    log_name_pattern: str = "{port}_{date}_{time}"
    log_max_days: int = 30
    log_max_total_size_mb: int = 500
    log_max_file_size_mb: int = 50
    log_auto_clean: bool = True
    serial_access_enabled: bool = True
    serial_access_password: str = ""
    serial_access_client_password: str = ""
    serial_access_max_clients: int = 16
    serial_access_default_permission: str = "read-write"
    serial_access_banned_ips: List[str] = field(default_factory=list)
    window_geometry: str = ""
    window_state: str = ""
    show_connections_panel: bool = True
    show_runtime_log_panel: bool = False
    show_command_sets_panel: bool = False
    command_sets_panel_width: int = 140
    command_sets: List[CommandSetData] = field(default_factory=list)
    highlight_rules: List[HighlightRuleData] = field(default_factory=list)

    @property
    def network_mode(self) -> str:
        return self.serial_access_mode

    @network_mode.setter
    def network_mode(self, value: str):
        self.serial_access_mode = value

    @property
    def network_host(self) -> str:
        return self.serial_access_host

    @network_host.setter
    def network_host(self, value: str):
        self.serial_access_host = value

    @property
    def network_port(self) -> int:
        return self.serial_access_port

    @network_port.setter
    def network_port(self, value: int):
        self.serial_access_port = value

    @property
    def server_address(self) -> str:
        return self.serial_access_server_address

    @server_address.setter
    def server_address(self, value: str):
        self.serial_access_server_address = value
