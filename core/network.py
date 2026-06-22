"""Compatibility exports for the renamed serial access server module."""

from .network_protocol import *  # noqa: F401,F403
from .serial_access_server import (
    SerialAccessClient as NetworkClient,
    SerialAccessConfig as NetworkConfig,
    SerialAccessMode as NetworkMode,
    SerialAccessServer as NetworkServer,
)

__all__ = [
    "NetworkClient",
    "NetworkConfig",
    "NetworkMode",
    "NetworkServer",
]
