"""Creates local shell sessions owned by MainWindow."""

from PyQt5.QtWidgets import QMessageBox

from core.local_shell_worker import LocalShellConfig, LocalShellWorker, shell_display_name
from ui.serial_tab import SerialTab


class LocalShellSessionController:
    """Creates local shell terminal sessions."""

    def __init__(self, main_window):
        self._main_window = main_window

    def create_session(self, config: LocalShellConfig):
        app_config = self._main_window.app_config
        session_key = self._session_key(config)

        if session_key in self._main_window._sessions:
            QMessageBox.warning(self._main_window, "Warning", f"Connection {session_key} already exists")
            return

        worker = LocalShellWorker(
            config,
            app_config.log_dir,
            log_enabled=app_config.log_enabled,
            log_timestamp=app_config.log_timestamp,
        )
        worker.state_changed.connect(lambda _state: self._main_window._refresh_connection_panel())

        tab = SerialTab(
            worker,
            app_config.scrollback_lines,
            font_family=getattr(app_config, "terminal_font_family", ""),
            font_size=getattr(app_config, "terminal_font_size", 11),
        )
        if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_highlight_rules"):
            tab.terminal.set_highlight_rules(getattr(app_config, "highlight_rules", []))

        tab_name = config.name or shell_display_name(config.command)
        index = self._main_window.tab_widget.addTab(tab, tab_name)
        self._main_window.tab_widget.setCurrentIndex(index)
        self._main_window._sessions[session_key] = (worker, tab, config)

        worker.start()
        self._main_window._refresh_connection_panel()
        self._main_window.statusbar.showMessage(f"Added local shell: {tab_name}")

    def _session_key(self, config: LocalShellConfig) -> str:
        command = config.command.replace("\\", "/")
        name = config.name or shell_display_name(config.command)
        return f"localshell://{name}@{command}"
