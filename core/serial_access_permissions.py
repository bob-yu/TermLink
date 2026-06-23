from dataclasses import dataclass, field
import time
from typing import List


PERMISSION_READ_ONLY = "read-only"
PERMISSION_READ_WRITE = "read-write"
VALID_PERMISSIONS = {PERMISSION_READ_ONLY, PERMISSION_READ_WRITE}


WRITE_ACTIONS = {"write", "write_data", "command", "send_command", "break", "send_break"}


def normalize_permission(value: str) -> str:
    return value if value in VALID_PERMISSIONS else PERMISSION_READ_WRITE


def client_ip(addr: str) -> str:
    return addr.rsplit(":", 1)[0] if ":" in addr else addr


@dataclass
class SerialAccessClientInfo:
    address: str
    ip: str
    permission: str
    authorized: bool = False
    connected: bool = True
    protocol: str = "gui"
    opened_ports: List[str] = field(default_factory=list)
    selected_port: str = ""
    connected_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    read_count: int = 0
    write_count: int = 0
    call_count: int = 0
    last_action: str = ""

    @property
    def label(self) -> str:
        ports = self.opened_ports or ([self.selected_port] if self.selected_port else [])
        port_text = ",".join(ports)
        if port_text:
            return f"{self.address}:{port_text} [{self.permission}]"
        return f"{self.address} [{self.permission}]"
