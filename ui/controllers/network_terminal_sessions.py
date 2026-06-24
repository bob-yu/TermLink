from PyQt5.QtWidgets import QMessageBox

from ui.serial_tab import SerialTab


class NetworkTerminalSessionController:
    """Creates network terminal sessions owned by MainWindow."""

    def __init__(self, main_window):
        self._main_window = main_window

    def create_session(self, config):
        session_key, tab_name, worker = self._build_worker(config)

        if session_key in self._main_window._sessions:
            QMessageBox.warning(self._main_window, "Warning", f"Connection {session_key} already exists")
            return

        worker.set_auto_reconnect(
            self._main_window.app_config.auto_reconnect,
            self._main_window.app_config.reconnect_interval,
        )
        if hasattr(worker, "state_changed"):
            worker.state_changed.connect(lambda _state: self._main_window._refresh_connection_panel())

        app_config = self._main_window.app_config
        tab = SerialTab(
            worker,
            app_config.scrollback_lines,
            font_family=getattr(app_config, "terminal_font_family", ""),
            font_size=getattr(app_config, "terminal_font_size", 11),
        )
        if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_highlight_rules"):
            tab.terminal.set_highlight_rules(getattr(app_config, "highlight_rules", []))
        index = self._main_window.tab_widget.addTab(tab, tab_name)
        self._main_window.tab_widget.setCurrentIndex(index)
        self._main_window._sessions[session_key] = (worker, tab, config)

        worker.start()
        self._main_window._refresh_connection_panel()
        self._main_window.statusbar.showMessage(f"Added connection: {tab_name}")

    def _build_worker(self, config):
        from core.ssh_worker import RawTcpConfig, RawTcpWorker, SSHConfig, SSHWorker, TelnetWorker

        app_config = self._main_window.app_config
        if isinstance(config, SSHConfig):
            session_key = f"ssh://{config.host}:{config.port}"
            tab_name = config.name or f"SSH:{config.host}"
            worker = SSHWorker(
                config,
                app_config.log_dir,
                log_enabled=app_config.log_enabled,
                log_timestamp=app_config.log_timestamp,
            )
            return session_key, tab_name, worker

        if isinstance(config, RawTcpConfig):
            session_key = f"rawtcp://{config.host}:{config.port}"
            tab_name = config.name or f"Raw TCP:{config.host}"
            worker = RawTcpWorker(
                config,
                app_config.log_dir,
                log_enabled=app_config.log_enabled,
                log_timestamp=app_config.log_timestamp,
            )
            return session_key, tab_name, worker

        session_key = f"telnet://{config.host}:{config.port}"
        tab_name = config.name or f"Telnet:{config.host}"
        worker = TelnetWorker(
            config,
            app_config.log_dir,
            log_enabled=app_config.log_enabled,
            log_timestamp=app_config.log_timestamp,
        )
        return session_key, tab_name, worker
