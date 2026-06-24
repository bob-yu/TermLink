import os
import subprocess
import sys

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeyEvent, QKeySequence
from PyQt5.QtWidgets import (
    QMessageBox,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

from core.data_bus import get_data_bus
from core.login_state_machine import LoginState
from core.serial_worker import WorkerState
from .terminal_widget import TerminalWidget


class SerialTab(QWidget):
    """One terminal tab for a local, remote, SSH, or Telnet session."""

    device_info_updated = pyqtSignal(str, str)  # (version, ip)
    title_changed = pyqtSignal(str)

    def __init__(
        self,
        worker,
        scrollback_lines: int = 5000,
        parent=None,
        font_family: str = "",
        font_size: int = 11,
    ):
        super().__init__(parent)
        self.worker = worker
        self._scrollback_lines = scrollback_lines
        self._font_family = font_family
        self._font_size = font_size
        self._data_bus = get_data_bus()
        self._subscribed = False
        self._device_version = ""
        self._device_ip = ""
        self._base_title = ""
        self._state_prefix = "[Disconnected]"
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._setup_device_info_check()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.terminal = TerminalWidget(
            self._send_data,
            self._scrollback_lines,
            font_family=self._font_family,
            font_size=self._font_size,
        )
        self.terminal.terminal_resized.connect(self._resize_worker_terminal)
        layout.addWidget(self.terminal, 1)
        self.terminal.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self._should_enter_connect():
            self._connect_session()
            event.accept()
            return
        super().keyPressEvent(event)

    def _should_enter_connect(self) -> bool:
        focused = self.focusWidget()
        if focused is self.terminal or self.terminal.isAncestorOf(focused):
            return False
        return not self.worker.is_connected

    def _setup_shortcuts(self):
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self._show_search)

        find_next_shortcut = QShortcut(QKeySequence("F3"), self)
        find_next_shortcut.activated.connect(self._find_next)

        find_prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        find_prev_shortcut.activated.connect(self._find_previous)

    def _connect_signals(self):
        if hasattr(self.worker, "source_id"):
            self._data_bus.subscribe(self.worker.source_id, self._on_data_from_bus)
            self._subscribed = True
        else:
            self.worker.data_received.connect(self._on_data_received)

        self.worker.state_changed.connect(self._on_state_changed)
        self.worker.error_occurred.connect(self._on_error)

        if hasattr(self.worker, "login_state_changed"):
            self.worker.login_state_changed.connect(self._on_login_state_changed)

        if hasattr(self.worker, "device_info_received"):
            self.worker.device_info_received.connect(self._on_device_info_received)

    def _setup_device_info_check(self):
        self._device_info_timer = QTimer(self)
        self._device_info_timer.setSingleShot(True)
        self._device_info_timer.timeout.connect(self._check_and_get_device_info)

    def _start_device_info_timer(self):
        # Do not probe automatically. Probing sends shell commands and should be explicit.
        return

    def _check_and_get_device_info(self):
        if hasattr(self.worker, "request_device_info") and self.worker.is_connected:
            self.worker.request_device_info()

    @pyqtSlot(str, str)
    def _on_device_info_received(self, version: str, ip: str):
        self._device_version = version
        self._device_ip = ip
        self.device_info_updated.emit(version, ip)

    def _on_data_from_bus(self, data: str):
        self.terminal.feed(data)

    @pyqtSlot(str)
    def _on_data_received(self, data: str):
        self.terminal.feed(data)

    def _send_data(self, data: str):
        if self.worker.is_connected:
            self.worker.write(data)

    def _resize_worker_terminal(self, cols: int, rows: int):
        if hasattr(self.worker, "resize"):
            self.worker.resize(cols, rows)

    def _show_search(self):
        self.terminal.show_search_dialog()

    def _find_next(self):
        if hasattr(self.terminal, "_view"):
            self.terminal._view.find_next()

    def _find_previous(self):
        if hasattr(self.terminal, "_view"):
            self.terminal._view.find_previous()

    @pyqtSlot(WorkerState)
    def _on_state_changed(self, state: WorkerState):
        self._state_prefix = {
            WorkerState.STOPPED: "[Disconnected]",
            WorkerState.DISCONNECTED: "[Disconnected]",
            WorkerState.CONNECTING: "[Connecting]",
            WorkerState.CONNECTED: "[Connected]",
            WorkerState.ERROR: "[Error]",
        }.get(state, "[Unknown]")
        self._emit_title()
        if state == WorkerState.CONNECTED:
            self._start_device_info_timer()
            return
        self._device_info_timer.stop()

    @pyqtSlot(LoginState)
    def _on_login_state_changed(self, state: LoginState):
        return

    @pyqtSlot(str)
    def _on_error(self, error: str):
        self.terminal.feed(f"\r\n\x1b[31m[ERROR] {error}\x1b[0m\r\n")

    def _connect_session(self):
        if not self.worker.is_connected:
            self.worker.start()

    def _disconnect_session(self):
        if self._is_remote_session():
            window = self.window()
            remote_sessions = getattr(window, "_remote_serial_sessions", None)
            if remote_sessions and remote_sessions.close_session_for_worker(self.worker):
                return
        if self.worker.is_connected:
            self.worker.stop()

    def _is_session_connected(self) -> bool:
        return bool(self.worker.is_connected)

    def set_base_title(self, title: str):
        self._base_title = title
        self._emit_title()

    def display_title(self) -> str:
        title = self._base_title or "Session"
        return f"{self._state_prefix} {title}"

    def _emit_title(self):
        if self._base_title:
            self.title_changed.emit(self.display_title())

    def close_session(self):
        if self._subscribed and hasattr(self.worker, "source_id"):
            self._data_bus.unsubscribe(self.worker.source_id, self._on_data_from_bus)
            self._subscribed = False
        self.worker.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self.terminal.setFocus()

    def _send_serial_break(self):
        if hasattr(self.worker, "send_break"):
            self.worker.send_break()
            self.terminal.feed("\r\n\x1b[33m[SysRq] Break sent, waiting for command key...\x1b[0m\r\n")

    def _toggle_log(self, enabled: bool):
        if hasattr(self.worker, "_logger") and self.worker._logger:
            self.worker._logger.enabled = enabled
            if hasattr(self.terminal, "_view"):
                self.terminal._view._log_enabled = enabled
            status = "started" if enabled else "stopped"
            self.terminal.feed(f"\r\n\x1b[33m[Log] Recording {status}\x1b[0m\r\n")

    def _is_remote_session(self) -> bool:
        return hasattr(self.worker, "_network_client") and hasattr(self.worker, "_remote_port")

    def _open_log_file(self):
        if self._is_remote_session():
            QMessageBox.information(
                self,
                "Info",
                "This is a remote serial session. Logs are stored on the server.",
            )
            return

        log_path = ""
        if hasattr(self.worker, "log_filepath"):
            log_path = self.worker.log_filepath
        elif hasattr(self.worker, "_logger") and self.worker._logger:
            log_path = self.worker._logger.filepath

        if log_path and os.path.exists(log_path):
            self._open_path(log_path)
        else:
            QMessageBox.information(self, "Info", "No log file is available for this session.")

    def _open_log_folder(self):
        if self._is_remote_session():
            QMessageBox.information(
                self,
                "Info",
                "This is a remote serial session. Logs are stored on the server.",
            )
            return

        log_path = ""
        if hasattr(self.worker, "log_filepath"):
            log_path = self.worker.log_filepath
        elif hasattr(self.worker, "_logger") and self.worker._logger:
            log_path = self.worker._logger.filepath

        if log_path:
            folder = os.path.dirname(log_path)
            if os.path.exists(folder):
                self._open_path(folder)
                return

        default_log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if os.path.exists(default_log_dir):
            self._open_path(default_log_dir)
        else:
            QMessageBox.information(self, "Info", "Log folder does not exist.")

    def _open_path(self, path: str):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Cannot open path: {exc}")
