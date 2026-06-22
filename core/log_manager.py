"""Log file naming, cleanup, and rotation."""

import os
import threading
import time
from datetime import datetime
from typing import Optional


class LogManager:
    """Manage the serial log-file lifecycle."""

    def __init__(
        self,
        log_dir: str,
        name_pattern: str = "{port}_{date}_{time}",
        max_days: int = 30,
        max_total_size_mb: int = 500,
        max_file_size_mb: int = 50,
        auto_clean: bool = True,
    ):
        self.log_dir = log_dir
        self.name_pattern = name_pattern
        self.max_days = max_days
        self.max_total_size_mb = max_total_size_mb
        self.max_file_size_mb = max_file_size_mb
        self.auto_clean = auto_clean
        self._lock = threading.Lock()

    def generate_filename(self, port_name: str, port_alias: str = "") -> str:
        """Generate a log filename from the configured pattern.

        Supported variables:
        - ``{port}``: sanitized port name, such as COM3 or ttyUSB0
        - ``{date}``: current date as YYYYMMDD
        - ``{time}``: current time as HHMMSS
        - ``{name}``: sanitized port alias, or the port when alias is empty
        """
        now = datetime.now()
        safe_port = port_name.replace("/", "_").replace("\\", "_").replace(":", "_")
        safe_alias = (port_alias or safe_port).replace("/", "_").replace("\\", "_").replace(":", "_")

        filename = self.name_pattern.format(
            port=safe_port,
            date=now.strftime("%Y%m%d"),
            time=now.strftime("%H%M%S"),
            name=safe_alias,
        )
        if not filename.endswith(".log"):
            filename += ".log"
        return filename

    def cleanup(self):
        """Run one complete cleanup pass."""
        if not self.auto_clean:
            return
        with self._lock:
            self._clean_empty_files()
            self._clean_by_days()
            self._clean_by_total_size()

    def cleanup_async(self):
        """Run cleanup on a background thread."""
        thread = threading.Thread(target=self.cleanup, daemon=True)
        thread.start()

    def get_stats(self) -> dict:
        """Return log directory statistics."""
        total_size = 0
        file_count = 0
        if os.path.isdir(self.log_dir):
            for name in os.listdir(self.log_dir):
                path = os.path.join(self.log_dir, name)
                if os.path.isfile(path) and name.endswith(".log"):
                    total_size += os.path.getsize(path)
                    file_count += 1
        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
        }

    def force_cleanup(self):
        """Run cleanup regardless of the auto-clean setting."""
        with self._lock:
            self._clean_empty_files()
            self._clean_by_days()
            self._clean_by_total_size()

    def _log_files_sorted(self):
        """Return log files sorted from oldest to newest."""
        if not os.path.isdir(self.log_dir):
            return []
        files = []
        for name in os.listdir(self.log_dir):
            path = os.path.join(self.log_dir, name)
            if os.path.isfile(path) and name.endswith(".log"):
                files.append(path)
        files.sort(key=lambda path: os.path.getmtime(path))
        return files

    def _clean_empty_files(self):
        """Delete zero-byte log files that have been idle for over one hour."""
        threshold = time.time() - 3600
        for path in self._log_files_sorted():
            try:
                if os.path.getsize(path) == 0 and os.path.getmtime(path) < threshold:
                    os.remove(path)
            except OSError:
                pass

    def _clean_by_days(self):
        """Delete logs older than the retention window."""
        if self.max_days <= 0:
            return
        cutoff = time.time() - self.max_days * 86400
        for path in self._log_files_sorted():
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass

    def _clean_by_total_size(self):
        """Delete oldest logs until the total size is under the limit."""
        if self.max_total_size_mb <= 0:
            return
        max_bytes = self.max_total_size_mb * 1024 * 1024
        files = self._log_files_sorted()
        total = sum(os.path.getsize(path) for path in files if os.path.exists(path))
        for path in files:
            if total <= max_bytes:
                break
            try:
                size = os.path.getsize(path)
                os.remove(path)
                total -= size
            except OSError:
                pass

    def check_rotation(self, filepath: str) -> Optional[str]:
        """Return a new path when the current log file should rotate."""
        if self.max_file_size_mb <= 0:
            return None
        try:
            if os.path.getsize(filepath) < self.max_file_size_mb * 1024 * 1024:
                return None
        except OSError:
            return None

        base, ext = os.path.splitext(filepath)
        index = 1
        while True:
            new_path = f"{base}_{index}{ext}"
            if not os.path.exists(new_path):
                return new_path
            index += 1
