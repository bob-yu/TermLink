"""Lightweight logger for remote serial sessions."""

import os
import threading
from datetime import datetime


class RemoteLogger:
    """Record remote-session commands, events, and errors.

    Remote sessions do not duplicate full serial output logs; the server-side
    serial logger remains the source of truth for raw terminal data.
    """

    def __init__(self, remote_port: str, log_dir: str = "logs"):
        self.remote_port = remote_port
        self.log_dir = log_dir
        self._file = None
        self._lock = threading.Lock()
        self._ensure_log_dir()
        self._open_log_file()

    def _ensure_log_dir(self):
        """Create the log directory when needed."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _open_log_file(self):
        """Open a new remote-session log file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_port_name = self.remote_port.replace("/", "_").replace("\\", "_").replace(":", "_")
        filename = f"remote_{safe_port_name}_{timestamp}.log"
        filepath = os.path.join(self.log_dir, filename)
        self._file = open(filepath, "w", encoding="utf-8")
        self._filepath = filepath

    @property
    def filepath(self) -> str:
        """Return the current log file path."""
        return self._filepath

    def log_command(self, command: str):
        """Record a user command."""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [COMMAND] {command}\n")
                self._file.flush()

    def log_event(self, event: str):
        """Record a session event."""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [EVENT] {event}\n")
                self._file.flush()

    def log_error(self, error: str):
        """Record a session error."""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [ERROR] {error}\n")
                self._file.flush()

    def close(self):
        """Close the log file."""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None

    def __del__(self):
        self.close()
