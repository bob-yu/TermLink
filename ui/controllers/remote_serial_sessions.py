from core.login_state_machine import LoginConfig
from core.remote_session_keys import (
    is_remote_session_key,
    make_remote_session_key,
    remote_session_port,
    remote_session_server_id,
    remote_tab_name,
)
from core.remote_worker import RemoteSerialWorkerProxy
from ui.serial_tab import SerialTab
from utils.config_schema import PortConfigData
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)
from PyQt5.QtCore import Qt


class RemotePortSelectionDialog(QDialog):
    """Select one or more remote serial ports to add as sessions."""

    def __init__(self, ports, opened_ports=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Remote Serial Ports")
        self.setMinimumSize(320, 360)
        opened_ports = set(opened_ports or [])

        layout = QVBoxLayout(self)
        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for port in ports:
            item = QListWidgetItem(port)
            item.setData(Qt.UserRole, port)
            if port in opened_ports:
                item.setText(f"{port} (opened)")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
            self._list.addItem(item)
        if ports:
            self._list.setCurrentRow(0)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_ports(self):
        return [item.data(Qt.UserRole) or item.text() for item in self._list.selectedItems()]


class RemoteSerialSessionController:
    """Creates and updates remote serial sessions owned by MainWindow."""

    def __init__(self, main_window):
        self._main_window = main_window
        self._select_next_port_list = set()
        self._last_ports_by_server = {}

    def request_port_selection(self, server_id: str = ""):
        self._select_next_port_list.add(server_id)

    def show_cached_port_selection(self, server_id: str = ""):
        selected_ports = self._select_ports(
            self._last_ports_by_server.get(server_id, []),
            server_id,
        )
        for port in selected_ports:
            self.create_session(port, server_id)

    def on_port_list_received(self, ports: list, server_id: str = ""):
        self._last_ports_by_server[server_id] = list(ports)
        self._main_window.statusbar.showMessage(
            f"Received {len(ports)} remote serial port(s) from {server_id or 'remote server'}"
        )
        if server_id not in self._select_next_port_list:
            self._main_window._refresh_connection_panel()
            return
        self._select_next_port_list.discard(server_id)
        selected_ports = self._select_ports(ports, server_id)
        for port in selected_ports:
            self.create_session(port, server_id)

    def on_port_added(self, port: str, server_id: str = ""):
        ports = self._last_ports_by_server.setdefault(server_id, [])
        if port not in ports:
            ports.append(port)
        self._main_window.statusbar.showMessage(f"{server_id or 'Server'} added serial port: {port}")
        self._main_window._refresh_connection_panel()

    def on_port_removed(self, port: str, server_id: str = ""):
        self._main_window.statusbar.showMessage(f"{server_id or 'Server'} removed serial port: {port}")
        ports = self._last_ports_by_server.setdefault(server_id, [])
        if port in ports:
            ports.remove(port)
        remote_key = make_remote_session_key(port, server_id)
        if remote_key not in self._main_window._sessions:
            return

        worker, tab, _ = self._main_window._sessions.pop(remote_key)
        tab.close_session()
        worker.stop()
        self._remove_tab(tab)
        self._main_window._refresh_connection_panel()

    def on_port_renamed(self, port: str, new_name: str, server_id: str = ""):
        remote_key = make_remote_session_key(port, server_id)
        if remote_key not in self._main_window._sessions:
            return

        _worker, tab, config = self._main_window._sessions[remote_key]
        tab_name = self._remote_display_name(new_name)
        if hasattr(tab, "set_base_title"):
            tab.set_base_title(tab_name)
        else:
            self._main_window._set_tab_title(tab, tab_name)
        config.name = tab_name
        self._main_window.statusbar.showMessage(f"Remote serial updated: {new_name}")

    def on_device_info(self, port: str, version: str, ip: str, server_id: str = ""):
        if hasattr(self._main_window, "_remote_device_info_cache"):
            self._main_window._remote_device_info_cache[(server_id, port)] = (version, ip)

        remote_key = make_remote_session_key(port, server_id)
        if remote_key in self._main_window._sessions:
            _worker, tab, _config = self._main_window._sessions[remote_key]
            self._main_window._update_tab_tooltip(tab, version, ip)

    def on_data_received(self, port: str, data: str, server_id: str = ""):
        remote_key = make_remote_session_key(port, server_id)
        if remote_key not in self._main_window._sessions:
            return

        worker, tab, _ = self._main_window._sessions[remote_key]
        tab.terminal.feed(data)
        if hasattr(worker, "_login_machine") and worker._login_machine and worker._auto_login_enabled:
            worker._login_machine.feed(data)

    def create_session(self, remote_port: str, server_id: str = ""):
        remote_key = make_remote_session_key(remote_port, server_id)
        if remote_key in self._main_window._sessions:
            return

        client = self._network_client_for_server(server_id)
        if not client:
            self._main_window.statusbar.showMessage(f"Remote server is not connected: {server_id}")
            return

        worker = RemoteSerialWorkerProxy(client, remote_port)
        if hasattr(worker, "state_changed"):
            worker.state_changed.connect(lambda _state: self._main_window._refresh_connection_panel())
        worker.setup_login(self._make_login_config())
        worker.set_auto_commands(self._main_window._default_auto_commands)
        worker.set_keywords(self._main_window._default_keywords)

        app_config = self._main_window.app_config
        tab = SerialTab(
            worker,
            app_config.scrollback_lines,
            font_family=getattr(app_config, "terminal_font_family", ""),
            font_size=getattr(app_config, "terminal_font_size", 11),
        )
        if hasattr(tab, "terminal") and hasattr(tab.terminal, "set_highlight_rules"):
            tab.terminal.set_highlight_rules(getattr(app_config, "highlight_rules", []))
        tab_name = self._remote_display_name(remote_port, server_id)
        display_name = tab_name
        if hasattr(tab, "set_base_title"):
            tab.set_base_title(tab_name)
            tab.title_changed.connect(lambda title, t=tab: self._main_window._set_tab_title(t, title))
            display_name = tab.display_title()
        index = self._main_window.tab_widget.addTab(tab, display_name)
        self._apply_cached_device_info_or_placeholder(index, tab, tab_name, remote_port, server_id)

        port_config = PortConfigData(
            name=tab_name,
            port=remote_key,
            baudrate=115200,
            login=self._main_window._default_login,
        )
        self._main_window._sessions[remote_key] = (worker, tab, port_config)
        worker.start()
        self._main_window._refresh_connection_panel()
        self._main_window.statusbar.showMessage(f"Added remote serial port: {tab_name}")

    def close_all(self):
        remote_sessions = [
            port for port in self._main_window._sessions
            if is_remote_session_key(port)
        ]
        for port in remote_sessions:
            self.close_session_by_key(port, refresh=False, disconnect_if_empty=False)
        self._disconnect_unused_clients()
        self._main_window._refresh_connection_panel()

    def close_session_by_key(
        self,
        remote_key: str,
        refresh: bool = True,
        disconnect_if_empty: bool = True,
    ) -> bool:
        if not is_remote_session_key(remote_key) or remote_key not in self._main_window._sessions:
            return False
        worker, tab, _ = self._main_window._sessions.pop(remote_key)
        tab.close_session()
        worker.stop()
        self._remove_tab(tab)
        if disconnect_if_empty:
            self._disconnect_unused_clients()
        if refresh:
            self._main_window._refresh_connection_panel()
        return True

    def close_session_for_worker(self, worker, refresh: bool = True) -> bool:
        for key, (session_worker, _tab, _config) in list(self._main_window._sessions.items()):
            if session_worker is worker and is_remote_session_key(key):
                return self.close_session_by_key(key, refresh=refresh)
        return False

    def has_remote_sessions(self) -> bool:
        return any(is_remote_session_key(key) for key in self._main_window._sessions)

    def _disconnect_unused_clients(self):
        remote_clients = getattr(self._main_window, "_remote_clients", None)
        if remote_clients is None:
            if self.has_remote_sessions():
                return
            client = getattr(self._main_window, "_network_client", None)
            if client:
                client.disconnect()
                self._main_window._network_client = None
            return

        used_server_ids = {
            remote_session_server_id(key)
            for key in self._main_window._sessions
            if is_remote_session_key(key)
        }
        for server_id in list(remote_clients.server_ids()):
            if server_id not in used_server_ids:
                if hasattr(self._main_window, "_serial_access_controller"):
                    self._main_window._serial_access_controller.remove_client(server_id)
                else:
                    remote_clients.remove(server_id)
        self._main_window._network_client = remote_clients.get(remote_clients.active_server_id)
        if hasattr(self._main_window, "_remote_device_info_cache"):
            self._main_window._remote_device_info_cache = {
                key: value
                for key, value in self._main_window._remote_device_info_cache.items()
                if not isinstance(key, tuple) or key[0] in used_server_ids
            }
        if hasattr(self._main_window, "_serial_access_controller"):
            self._main_window._serial_access_controller.update_log_download_menu_visibility()

    def _make_login_config(self):
        default_login = self._main_window._default_login
        return LoginConfig(
            username=default_login.username,
            password=default_login.password,
            login_prompt=default_login.login_prompt,
            password_prompt=default_login.password_prompt,
            shell_prompts=default_login.shell_prompt,
        )

    def _apply_cached_device_info_or_placeholder(self, index: int, tab, tab_name: str, remote_port: str, server_id: str):
        cache_key = (server_id, remote_port)
        if (
            hasattr(self._main_window, "_remote_device_info_cache")
            and cache_key in self._main_window._remote_device_info_cache
        ):
            version, ip = self._main_window._remote_device_info_cache[cache_key]
            self._main_window._update_tab_tooltip(tab, version, ip)
            return

        self._main_window.tab_widget.setTabToolTip(index, f"{tab_name}\nWaiting for device information...")

    def _remove_tab(self, tab):
        for i in range(self._main_window.tab_widget.count()):
            if self._main_window.tab_widget.widget(i) == tab:
                self._main_window.tab_widget.removeTab(i)
                break

    def _select_ports(self, ports, server_id: str = ""):
        opened_ports = [
            remote_session_port(key)
            for key in self._main_window._sessions
            if is_remote_session_key(key) and remote_session_server_id(key) == server_id
        ]
        dialog = RemotePortSelectionDialog(ports, opened_ports, self._main_window)
        if dialog.exec_() != QDialog.Accepted:
            return []
        return dialog.selected_ports()

    def _remote_display_name(self, remote_port: str, server_id: str = "") -> str:
        if not server_id:
            address = getattr(self._main_window.app_config, "serial_access_server_address", "")
            server_id = address
        host = server_id.rsplit(":", 1)[0] if ":" in server_id else server_id
        if host == "0.0.0.0":
            host = "127.0.0.1"
        port_name = remote_port.split("/")[-1] if "/" in remote_port else remote_port
        if host:
            return f"{host}:{port_name}"
        return remote_tab_name(remote_port)

    def _network_client_for_server(self, server_id: str):
        remote_clients = getattr(self._main_window, "_remote_clients", None)
        if remote_clients is not None:
            return remote_clients.get(server_id)
        return getattr(self._main_window, "_network_client", None)
