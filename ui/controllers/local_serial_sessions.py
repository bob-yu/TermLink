from PyQt5.QtWidgets import QMessageBox

from core.login_state_machine import LoginConfig
from core.serial_access_server import SerialAccessMode
from core.serial_worker import SerialConfig, SerialWorker
from ui.serial_tab import SerialTab


class LocalSerialSessionController:
    """Creates local serial sessions owned by MainWindow."""

    def __init__(self, main_window):
        self._main_window = main_window

    def create_session(self, port_config):
        port = port_config.port
        if port in self._main_window._sessions:
            QMessageBox.warning(self._main_window, "Warning", f"Serial port {port} is already open")
            return

        worker = self._create_worker(port_config)
        self._connect_worker_signals(worker, port)
        self._configure_worker(worker, port_config)
        tab = self._create_tab(worker, port_config)

        self._main_window._sessions[port] = (worker, tab, port_config)
        self._main_window._update_server_port_list()
        self._main_window._refresh_connection_panel()
        self._main_window.statusbar.showMessage(f"Added serial port: {port}")

    def _create_worker(self, port_config):
        serial_config = SerialConfig(
            port=port_config.port,
            baudrate=port_config.baudrate,
            bytesize=port_config.data_bits,
            parity=port_config.parity,
            stopbits=port_config.stop_bits,
            flow_control=port_config.flow_control,
            name=port_config.name,
        )
        app_config = self._main_window.app_config
        return SerialWorker(
            serial_config,
            app_config.log_dir,
            log_enabled=app_config.log_enabled,
            log_timestamp=app_config.log_timestamp,
            log_manager=self._main_window._log_manager,
        )

    def _connect_worker_signals(self, worker, port: str):
        if hasattr(worker, "state_changed"):
            worker.state_changed.connect(lambda _state: self._main_window._refresh_connection_panel())
        worker.data_received.connect(
            lambda data, p=port: self._main_window._broadcast_serial_data(p, data)
        )
        worker.device_state_changed.connect(
            lambda old, new, detail, p=port: self._main_window._on_worker_device_state_changed(
                p,
                old,
                new,
                detail,
            )
        )

        if self._main_window._network_mode == SerialAccessMode.SERVER:
            worker.login_state_changed.connect(
                lambda state, p=port: self._main_window._on_server_login_state_changed(p, state)
            )
            worker.data_received.connect(
                lambda data, p=port: self._main_window._parse_ip_from_data(p, data)
            )

    def _configure_worker(self, worker, port_config):
        login_config = LoginConfig(
            username=port_config.login.username,
            password=port_config.login.password,
            login_prompt=port_config.login.login_prompt,
            password_prompt=port_config.login.password_prompt,
            shell_prompts=port_config.login.shell_prompt,
        )
        worker.setup_login(login_config)
        worker.set_auto_commands(port_config.auto_commands)
        worker.set_keywords(port_config.keywords)
        worker.set_auto_reconnect(
            self._main_window.app_config.auto_reconnect,
            self._main_window.app_config.reconnect_interval,
        )

    def _create_tab(self, worker, port_config):
        app_config = self._main_window.app_config
        tab = SerialTab(
            worker,
            app_config.scrollback_lines,
            font_family=getattr(app_config, "terminal_font_family", ""),
            font_size=getattr(app_config, "terminal_font_size", 11),
        )
        if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_highlight_rules"):
            tab.terminal.set_highlight_rules(getattr(app_config, "highlight_rules", []))
        port = port_config.port
        tab.device_info_updated.connect(
            lambda ver, ip, t=tab, p=port: self._main_window._on_device_info_updated(t, p, ver, ip)
        )

        tab_name = port_config.name or port
        display_name = tab_name
        if hasattr(tab, "set_base_title"):
            tab.set_base_title(tab_name)
            tab.title_changed.connect(lambda title, t=tab: self._main_window._set_tab_title(t, title))
            display_name = tab.display_title()
        index = self._main_window.tab_widget.addTab(tab, display_name)
        self._main_window.tab_widget.setCurrentIndex(index)
        self._main_window.tab_widget.setTabToolTip(
            index,
            (
                f"{tab_name}\nSerial: {port}\n"
                f"Config: {port_config.baudrate} "
                f"{port_config.data_bits}{port_config.parity}{port_config.stop_bits:g}"
                f"\nFlow control: {port_config.flow_control}"
            ),
        )
        return tab
