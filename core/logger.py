"""Serial log writer with optional timestamps and rotation support."""

import os
import re
import threading
from datetime import datetime
from typing import Optional

from .log_manager import LogManager


ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b[()][AB012]|\x1b[>=]"
)


class SerialLogger:
    """Thread-safe serial logger.

    The logger writes one file per port, can add timestamps, and delegates file
    naming plus rotation policy to ``LogManager`` when one is supplied.
    """

    def __init__(
        self,
        port_name: str,
        log_dir: str = "logs",
        enabled: bool = True,
        add_timestamp: bool = True,
        log_manager: Optional[LogManager] = None,
        port_alias: str = "",
    ):
        self.port_name = port_name
        self.log_dir = log_dir
        self._file = None
        self._lock = threading.Lock()
        self._enabled = enabled
        self._add_timestamp = add_timestamp
        self._filepath = ""
        self._log_manager = log_manager
        self._port_alias = port_alias
        self._write_count = 0

        if self._enabled:
            self._ensure_log_dir()
            self._open_log_file()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        with self._lock:
            if value and not self._enabled:
                self._enabled = True
                self._ensure_log_dir()
                self._open_log_file()
            elif not value and self._enabled:
                self._enabled = False
                if self._file:
                    self._file.close()
                    self._file = None

    def _ensure_log_dir(self):
        """Create the log directory when needed."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

    def _open_log_file(self):
        """Open the current log file."""
        if self._log_manager:
            filename = self._log_manager.generate_filename(
                self.port_name, self._port_alias
            )
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_port = self.port_name.replace("/", "_").replace("\\", "_").replace(":", "_")
            filename = f"{safe_port}_{timestamp}.log"

        filepath = os.path.join(self.log_dir, filename)
        self._file = open(filepath, "w", encoding="utf-8")
        self._filepath = filepath

    @property
    def filepath(self) -> str:
        """Return the current log file path."""
        return self._filepath

    def write(self, data: str, add_timestamp: bool = None):
        """Write data to the log file."""
        if not self._enabled:
            return

        if add_timestamp is None:
            add_timestamp = self._add_timestamp

        with self._lock:
            if self._file is None:
                return

            if add_timestamp:
                clean_data = ANSI_ESCAPE_PATTERN.sub("", data)
                normalized_data = clean_data.replace("\r\n", "\n").replace("\r", "\n")
                lines = normalized_data.split("\n")
                for line in lines:
                    line = line.rstrip()
                    if line:
                        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                        self._file.write(f"{timestamp} {line}\n")
            else:
                self._file.write(data)

            self._file.flush()

            self._write_count += 1
            if self._write_count >= 100:
                self._write_count = 0
                self._check_rotation()

    def _check_rotation(self):
        """Rotate the log file when the manager says it is too large."""
        if not self._log_manager or not self._filepath:
            return
        new_path = self._log_manager.check_rotation(self._filepath)
        if new_path:
            if self._file:
                self._file.close()
            self._file = open(new_path, "w", encoding="utf-8")
            self._filepath = new_path

    def write_raw(self, data: str):
        """Write raw data without adding timestamps."""
        self.write(data, add_timestamp=False)

    def write_event(self, event: str):
        """Write an event line."""
        if not self._enabled:
            return
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [EVENT] {event}\n")
                self._file.flush()

    def close(self):
        """Close the current log file."""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None

    def __del__(self):
        self.close()
