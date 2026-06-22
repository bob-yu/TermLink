from PyQt5.QtWidgets import QDialog, QMessageBox

from core.network_address import parse_server_address
from core.remote_session_keys import is_remote_session_key
from core.serial_access_client import SerialAccessClient
from core.serial_access_server import SerialAccessMode, SerialAccessServer
from ui.dialogs.remote_serial_dialog import RemoteSerialDialog
from ui.dialogs.serial_access_settings_dialog import SerialAccessSettingsDialog


class SerialAccessController:
    """Owns serial access server/client lifecycle for MainWindow."""

    def __init__(self, main_window):
        self._main_window = main_window

    def init_network(self):
        mode = self._main_window.app_config.serial_access_mode

        if mode == "server":
            self.start_server()
        elif self._main_window.app_config.serial_access_enabled:
            self.start_server()

        self.update_log_download_menu_visibility()

    def update_log_download_menu_visibility(self):
        remote_clients = getattr(self._main_window, "_remote_clients", None)
        if remote_clients is not None:
            self._main_window._download_logs_action.setVisible(
                bool(remote_clients.clients())
            )
            return
        self._main_window._download_logs_action.setVisible(
            self._main_window._network_client is not None
        )

    def start_server(self):
        if self._main_window._network_server:
            self._main_window._network_server.stop()

        config = self._main_window.app_config
        self._main_window._network_mode = SerialAccessMode.SERVER
        server = SerialAccessServer(
            config.serial_access_host,
            config.serial_access_port,
            config.log_dir,
            sessions_provider=lambda: self._main_window._sessions,
            access_password=config.serial_access_password,
            max_clients=config.serial_access_max_clients,
            default_permission=getattr(config, "serial_access_default_permission", "read-write"),
            banned_ips=getattr(config, "serial_access_banned_ips", []),
        )
        self._main_window._network_server = server
        self._main_window._serial_access_server = (
            server if config.serial_access_enabled else None
        )

        server.client_connected.connect(self._main_window._on_client_connected)
        server.client_disconnected.connect(self._main_window._on_client_disconnected)
        if hasattr(server, "client_updated"):
            server.client_updated.connect(self._main_window._on_client_updated)
        server.data_received.connect(self._main_window._on_network_data_received)
        server.break_requested.connect(self._main_window._on_break_requested)
        server.error_occurred.connect(self._main_window._on_network_error)
        server.start()

        self.update_server_port_list()
        self.update_log_download_menu_visibility()
        self._main_window.setWindowTitle(self._window_title())
        self._main_window._refresh_connection_panel()
        self._main_window.statusbar.showMessage(
            "Remote access server started. Add and connect ports manually."
        )

    def update_server_port_list(self):
        if not self._main_window._network_server:
            return

        ports = [
            port for port in self._main_window._sessions.keys()
            if not is_remote_session_key(port)
        ]
        self._main_window._network_server.update_port_list(ports)

    def start_client(self, server_address: str = "", access_password: str = ""):
        config = self._main_window.app_config
        server_address = server_address or config.serial_access_server_address
        access_password = access_password or getattr(
            config,
            "serial_access_client_password",
            config.serial_access_password,
        )
        if not server_address:
            QMessageBox.warning(
                self._main_window,
                "Error",
                "Configure the server address first.",
            )
            return

        server_addr = parse_server_address(
            server_address,
            config.serial_access_port,
        )
        server_id = f"{server_addr.host}:{server_addr.port}"
        client = SerialAccessClient(
            server_addr.host,
            server_addr.port,
            access_password,
        )
        if hasattr(self._main_window, "_remote_clients"):
            self._main_window._remote_clients.add(server_id, client)
        self._main_window._network_client = client

        client.connected.connect(lambda sid=server_id: self._main_window._on_server_connected(sid))
        client.disconnected.connect(lambda sid=server_id: self._main_window._on_server_disconnected(sid))
        client.port_list_received.connect(
            lambda ports, sid=server_id: self._main_window._on_port_list_received(sid, ports)
        )
        client.port_added.connect(
            lambda port, sid=server_id: self._main_window._on_remote_port_added(sid, port)
        )
        client.port_removed.connect(
            lambda port, sid=server_id: self._main_window._on_remote_port_removed(sid, port)
        )
        client.port_renamed.connect(
            lambda port, name, sid=server_id: self._main_window._on_remote_port_renamed(sid, port, name)
        )
        client.data_received.connect(
            lambda port, data, sid=server_id: self._main_window._on_remote_data_received(sid, port, data)
        )
        client.device_info_received.connect(
            lambda port, version, ip, sid=server_id: self._main_window._on_remote_device_info(sid, port, version, ip)
        )
        client.error_occurred.connect(self._main_window._on_network_error)
        client.connect_to_server()

        if not self._main_window._network_server:
            self._main_window._network_mode = SerialAccessMode.CLIENT
        self.update_log_download_menu_visibility()
        self._main_window.setWindowTitle(self._window_title())
        self._main_window._refresh_connection_panel()
        self._main_window.statusbar.showMessage(
            f"Connecting to remote access server {server_addr.host}:{server_addr.port}..."
        )

    def stop_network(self):
        if self._main_window._network_server:
            self._main_window._network_server.stop()
            self._main_window._network_server = None
            self._main_window._serial_access_server = None

        if hasattr(self._main_window, "_remote_clients"):
            self._main_window._remote_clients.clear()
            self._main_window._network_client = None
        elif self._main_window._network_client:
            self._main_window._network_client.disconnect()
            self._main_window._network_client = None

        if hasattr(self._main_window, "_remote_device_info_cache"):
            self._main_window._remote_device_info_cache.clear()

        self._main_window._remote_serial_sessions.close_all()
        self._main_window._network_mode = SerialAccessMode.DISABLED
        self.update_log_download_menu_visibility()
        self._main_window.setWindowTitle("TermLink")
        self._main_window._refresh_connection_panel()

    def show_settings(self):
        dialog = SerialAccessSettingsDialog(
            self._main_window.app_config,
            self._main_window,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        settings = dialog.get_settings()
        config = self._main_window.app_config
        config.serial_access_mode = "server" if settings.access_enabled else "disabled"
        config.serial_access_host = settings.host
        config.serial_access_port = settings.port
        config.serial_access_enabled = settings.access_enabled
        config.serial_access_password = settings.access_password
        config.serial_access_max_clients = settings.max_clients
        config.serial_access_default_permission = settings.default_permission
        self._main_window.config_manager.save()

        self.stop_network()
        self.init_network()
        self._main_window.statusbar.showMessage("Serial access configuration updated.")

    def show_remote_connection(self):
        dialog = RemoteSerialDialog(
            self._main_window.app_config,
            self._main_window,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        settings = dialog.get_settings()
        config = self._main_window.app_config
        config.serial_access_server_address = settings.server_address
        config.serial_access_client_password = settings.access_password
        self._main_window.config_manager.save()

        server_addr = parse_server_address(
            settings.server_address,
            config.serial_access_port,
        )
        server_id = f"{server_addr.host}:{server_addr.port}"
        remote_clients = getattr(self._main_window, "_remote_clients", None)
        existing_client = (
            remote_clients.connected_client(server_id)
            if remote_clients is not None
            else None
        )
        if existing_client:
            self._main_window._network_client = existing_client
            remote_clients.set_active(server_id)
            self._main_window._remote_serial_sessions.show_cached_port_selection(server_id)
            self._main_window.setWindowTitle(self._window_title())
            self.update_log_download_menu_visibility()
            return

        if remote_clients is not None and remote_clients.get(server_id):
            remote_clients.remove(server_id)
        elif self._main_window._network_client:
            self._main_window._network_client.disconnect()
            self._main_window._network_client = None

        self._main_window._remote_serial_sessions.request_port_selection(server_id)
        self.start_client(settings.server_address, settings.access_password)

    def remove_client(self, server_id: str, disconnect: bool = True):
        remote_clients = getattr(self._main_window, "_remote_clients", None)
        if remote_clients is None:
            if self._main_window._network_client and disconnect:
                self._main_window._network_client.disconnect()
            self._main_window._network_client = None
            return
        remote_clients.remove(server_id, disconnect=disconnect)
        self._main_window._network_client = remote_clients.get(remote_clients.active_server_id)
        self.update_log_download_menu_visibility()
        self._main_window.setWindowTitle(self._window_title())

    def _window_title(self) -> str:
        return "TermLink"

