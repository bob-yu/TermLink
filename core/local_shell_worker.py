"""Local shell worker backed by PTY/ConPTY."""

import os
import platform
import queue
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import List, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .data_bus import get_data_bus
from .logger import SerialLogger
from .serial_worker import WorkerState


@dataclass
class LocalShellConfig:
    """Configuration for a local interactive shell session."""

    command: str
    name: str = ""
    working_directory: str = ""
    encoding: str = "utf-8"
    cols: int = 80
    rows: int = 24


def default_shell_command() -> str:
    system = platform.system()
    if system == "Windows":
        for executable, arguments in (
            ("powershell.exe", "-NoLogo -NoProfile"),
            ("cmd.exe", ""),
            ("pwsh.exe", "-NoLogo -NoProfile"),
        ):
            resolved = shutil.which(executable)
            if resolved:
                return f"{executable} {arguments}".strip()
        return "cmd.exe"
    shell = os.environ.get("SHELL", "").strip()
    if shell and os.path.exists(shell):
        return shell
    for command in ("bash", "zsh", "sh"):
        resolved = shutil.which(command)
        if resolved:
            return resolved
    return "sh"


def shell_display_name(command: str) -> str:
    if not command:
        return "Local Shell"
    try:
        first = shlex.split(command, posix=platform.system() != "Windows")[0]
    except ValueError:
        first = command.split()[0]
    return os.path.basename(first).replace(".exe", "") or "Local Shell"


class LocalShellWorker(QObject):
    """Interactive local shell worker compatible with SerialTab."""

    data_received = pyqtSignal(str)
    state_changed = pyqtSignal(WorkerState)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        config: LocalShellConfig,
        log_dir: str = "logs",
        log_enabled: bool = True,
        log_timestamp: bool = True,
    ):
        super().__init__()
        self.config = config
        self._state = WorkerState.STOPPED
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._write_queue: "queue.Queue[str]" = queue.Queue()
        self._data_bus = get_data_bus()
        self._source_id = f"localshell://{id(self)}"
        self._logger = SerialLogger(
            config.name or f"local_shell_{shell_display_name(config.command)}",
            log_dir,
            enabled=log_enabled,
            add_timestamp=log_timestamp,
        )
        self._process = None
        self._master_fd: Optional[int] = None
        self._winpty = None
        self._pending_windows_cursor_move = ""
        if log_enabled:
            self._data_bus.register_log_handler(
                self._source_id,
                lambda data: self._logger.write(data),
            )

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == WorkerState.CONNECTED

    @property
    def log_filepath(self) -> str:
        return self._logger.filepath

    @property
    def source_id(self) -> str:
        return self._source_id

    def set_auto_reconnect(self, _enabled: bool, _interval: float = 5):
        return

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._terminate_shell()
        if self._writer_thread:
            self._writer_thread.join(timeout=1)
            self._writer_thread = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._logger.close()
        self._data_bus.unregister_log_handler(self._source_id)
        self._set_state(WorkerState.STOPPED)

    def write(self, data: str):
        if not self._running:
            return
        self._write_queue.put(data)

    def send_command(self, command: str):
        if not command.endswith("\n"):
            command += "\n"
        self.write(command)

    def resize(self, cols: int, rows: int):
        self.config.cols = max(20, int(cols))
        self.config.rows = max(5, int(rows))
        if platform.system() == "Windows":
            self._resize_windows()
        else:
            self._resize_posix()

    def _run(self):
        try:
            self._set_state(WorkerState.CONNECTING)
            if platform.system() == "Windows":
                self._run_windows()
            else:
                self._run_posix()
        except Exception as exc:
            if self._running:
                self.error_occurred.emit(f"Local shell error: {exc}")
                self._set_state(WorkerState.ERROR)
        finally:
            self._running = False
            self._terminate_shell()
            if self._state != WorkerState.STOPPED:
                self._set_state(WorkerState.DISCONNECTED)

    def _run_windows(self):
        try:
            import winpty
        except ImportError as exc:
            raise RuntimeError("Local Shell on Windows requires pywinpty. Run: pip install pywinpty") from exc

        cwd = self.config.working_directory or os.getcwd()
        process = winpty.PtyProcess.spawn(
            self.config.command,
            cwd=cwd,
            dimensions=(self.config.rows, self.config.cols),
        )
        self._winpty = process
        self._writer_thread = threading.Thread(
            target=self._windows_write_loop,
            args=(process,),
            daemon=True,
        )
        self._writer_thread.start()
        self._set_state(WorkerState.CONNECTED)

        while self._running and process.isalive():
            try:
                data = process.read(4096)
            except EOFError:
                break
            if data:
                self._publish(data)
            else:
                time.sleep(0.01)

    def _windows_write_loop(self, process):
        while self._running and process.isalive():
            try:
                data = self._write_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                process.write(data)
            except Exception as exc:
                if self._running:
                    self.error_occurred.emit(f"Send failed: {exc}")
                return

    def _resize_windows(self):
        process = self._winpty
        if not process:
            return
        try:
            process.setwinsize(self.config.rows, self.config.cols)
        except AttributeError:
            try:
                process.set_size(self.config.cols, self.config.rows)
            except AttributeError:
                return

    def _run_posix(self):
        import fcntl
        import pty

        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd
        self._resize_posix()
        command = self._command_args()
        cwd = self.config.working_directory or None
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
        self._process = process
        os.close(slave_fd)
        self._set_state(WorkerState.CONNECTED)

        while self._running and process.poll() is None:
            self._drain_writes_posix(master_fd)
            readable, _, _ = select.select([master_fd], [], [], 0.05)
            if readable:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                self._publish(data.decode(self.config.encoding, errors="replace"))

    def _command_args(self) -> List[str]:
        command = self.config.command.strip() or default_shell_command()
        return shlex.split(command, posix=True)

    def _drain_writes_posix(self, master_fd: int):
        while True:
            try:
                data = self._write_queue.get_nowait()
            except queue.Empty:
                return
            os.write(master_fd, data.encode(self.config.encoding, errors="replace"))

    def _resize_posix(self):
        if self._master_fd is None:
            return
        try:
            import fcntl
            import termios

            winsize = struct.pack("HHHH", self.config.rows, self.config.cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            return

    def _terminate_shell(self):
        if platform.system() == "Windows":
            if self._winpty:
                try:
                    self._winpty.terminate(force=True)
                except Exception:
                    pass
                self._winpty = None
            return

        process = self._process
        self._process = None
        if process and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except OSError:
                process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    process.kill()
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None

    def _publish(self, text: str):
        if platform.system() == "Windows":
            text = self._normalize_windows_shell_output(text)
        self._data_bus.publish(self._source_id, text)
        self.data_received.emit(text)

    def _normalize_windows_shell_output(self, text: str) -> str:
        cursor_pattern = r"\x1b\[\d+;1H"
        prompt_pattern = r"PS [^\r\n>]+> "

        if re.fullmatch(cursor_pattern, text):
            self._pending_windows_cursor_move = text
            return ""

        if self._pending_windows_cursor_move:
            pending = self._pending_windows_cursor_move
            self._pending_windows_cursor_move = ""
            if re.match(prompt_pattern, text):
                return "\r\n" + text
            text = pending + text

        return re.sub(cursor_pattern + r"(?=" + prompt_pattern + r")", "\r\n", text)

    def _set_state(self, state: WorkerState):
        if self._state != state:
            self._state = state
            self.state_changed.emit(state)
