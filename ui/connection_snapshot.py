from dataclasses import dataclass
from typing import List


@dataclass
class SessionSnapshot:
    key: str
    name: str
    connected: bool
    kind: str


@dataclass
class AccessSnapshot:
    summary: str
    details: List[str]
    clients: List[str]


@dataclass
class ConnectionSnapshot:
    sessions: List[SessionSnapshot]
    access: AccessSnapshot
