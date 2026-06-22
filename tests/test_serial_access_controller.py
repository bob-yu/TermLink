import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeServer:
    def __init__(
        self,
        host,
        port,
        log_dir,
        sessions_provider,
        access_password,
        max_clients=16,
        default_permission="read-write",
        banned_ips=None,
    ):
        self.host = host
        self.port = port
        self.log_dir = log_dir
        self.sessions_provider = sessions_provider
        self.access_password = access_password
        self.max_clients = max_clients
        self.default_permission = default_permission
        self.banned_ips = banned_ips or []
        self.client_connected = FakeSignal()
        self.client_disconnected = FakeSignal()
        self.client_updated = FakeSignal()
        self.data_received = FakeSignal()
        self.break_requested = FakeSignal()
        self.error_occurred = FakeSignal()
        self.started = False
        self.stopped = False
        self.ports = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def update_port_list(self, ports):
        self.ports = ports


class FakeClient:
    def __init__(self, host, port, access_password):
        self.host = host
        self.port = port
        self.access_password = access_password
        self.connected = FakeSignal()
        self.disconnected = FakeSignal()
        self.port_list_received = FakeSignal()
        self.port_added = FakeSignal()
        self.port_removed = FakeSignal()
        self.port_renamed = FakeSignal()
        self.data_received = FakeSignal()
        self.device_info_received = FakeSignal()
        self.error_occurred = FakeSignal()
        self.started = False
        self.disconnected_called = False
        self.is_connected = False

    def connect_to_server(self):
        self.started = True
        self.is_connected = True

    def disconnect(self):
        self.disconnected_called = True
        self.is_connected = False


class FakeAction:
    def __init__(self):
        self.visible = None

    def setVisible(self, visible):
        self.visible = visible


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class FakeRemoteSessions:
    def __init__(self):
        self.closed = False
        self.selection_requested = False

    def close_all(self):
        self.closed = True

    def request_port_selection(self, _server_id=""):
        self.selection_requested = True

    def show_cached_port_selection(self, _server_id=""):
        self.selection_requested = True


class FakeRemoteClients:
    def __init__(self):
        self._clients = {}
        self.active_server_id = ""

    def add(self, server_id, client):
        self._clients[server_id] = client
        self.active_server_id = server_id

    def get(self, server_id):
        return self._clients.get(server_id)

    def connected_client(self, server_id):
        client = self.get(server_id)
        return client if client and client.is_connected else None

    def remove(self, server_id, disconnect=True):
        client = self._clients.pop(server_id, None)
        if client and disconnect:
            client.disconnect()
        if self.active_server_id == server_id:
            self.active_server_id = next(iter(self._clients), "")

    def clear(self):
        for server_id in list(self._clients):
            self.remove(server_id)

    def clients(self):
        return dict(self._clients)

    def server_ids(self):
        return list(self._clients.keys())

    def set_active(self, server_id):
        self.active_server_id = server_id


class FakeConfigManager:
    def __init__(self):
        self.saved = False

    def save(self):
        self.saved = True


class FakeConfig:
    serial_access_mode = "disabled"
    serial_access_enabled = False
    serial_access_host = "0.0.0.0"
    serial_access_port = 56337
    serial_access_server_address = "127.0.0.1:56338"
    serial_access_password = "secret"
    serial_access_client_password = "client-secret"
    serial_access_max_clients = 16
    serial_access_default_permission = "read-write"
    serial_access_banned_ips = []
    log_dir = "logs"


class FakeMainWindow:
    def __init__(self):
        self.app_config = FakeConfig()
        self.config_manager = FakeConfigManager()
        self._sessions = {"COM1": object(), "remote://COM2": object()}
        self._download_logs_action = FakeAction()
        self._remote_serial_sessions = FakeRemoteSessions()
        self.statusbar = FakeStatusBar()
        self._network_mode = None
        self._network_server = None
        self._network_client = None
        self._remote_clients = FakeRemoteClients()
        self._serial_access_server = None
        self.titles = []
        self.refreshed = 0
        self._remote_device_info_cache = {"COM1": ("v1", "10.0.0.2")}

    def setWindowTitle(self, title):
        self.titles.append(title)

    def _refresh_connection_panel(self):
        self.refreshed += 1

    def _on_client_connected(self, _addr): pass
    def _on_client_disconnected(self, _addr): pass
    def _on_client_updated(self, _addr): pass
    def _on_network_data_received(self, _addr, _port, _data): pass
    def _on_break_requested(self, _addr, _port): pass
    def _on_network_error(self, _error): pass
    def _on_server_connected(self): pass
    def _on_server_disconnected(self): pass
    def _on_port_list_received(self, _ports): pass
    def _on_remote_port_added(self, _port): pass
    def _on_remote_port_removed(self, _port): pass
    def _on_remote_port_renamed(self, _port, _name): pass
    def _on_remote_data_received(self, _port, _data): pass
    def _on_remote_device_info(self, _port, _version, _ip): pass


def load_controller_module():
    pyqt5 = types.ModuleType("PyQt5")
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    qtcore = types.ModuleType("PyQt5.QtCore")

    class QDialog:
        Accepted = 1

    class QMessageBox:
        warnings = []

        @staticmethod
        def warning(parent, title, message):
            QMessageBox.warnings.append((parent, title, message))

    qtwidgets.QDialog = QDialog
    qtwidgets.QMessageBox = QMessageBox
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtWidgets"] = qtwidgets
    qtcore.QObject = object
    qtcore.pyqtSignal = lambda *args, **kwargs: FakeSignal()
    sys.modules["PyQt5.QtCore"] = qtcore

    ui_module = types.ModuleType("ui")
    ui_module.__path__ = []
    dialogs_module = types.ModuleType("ui.dialogs")
    dialogs_module.__path__ = []
    settings_module = types.ModuleType("ui.dialogs.serial_access_settings_dialog")
    remote_dialog_module = types.ModuleType("ui.dialogs.remote_serial_dialog")

    class SerialAccessSettingsDialog:
        next_result = QDialog.Accepted
        next_settings = None

        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return self.next_result

        def get_settings(self):
            return self.next_settings

    class RemoteSerialDialog:
        next_result = QDialog.Accepted
        next_settings = None

        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return self.next_result

        def get_settings(self):
            return self.next_settings

    settings_module.SerialAccessSettingsDialog = SerialAccessSettingsDialog
    remote_dialog_module.RemoteSerialDialog = RemoteSerialDialog
    sys.modules["ui"] = ui_module
    sys.modules["ui.dialogs"] = dialogs_module
    sys.modules["ui.dialogs.serial_access_settings_dialog"] = settings_module
    sys.modules["ui.dialogs.remote_serial_dialog"] = remote_dialog_module

    path = Path(__file__).resolve().parents[1] / "ui" / "controllers" / "serial_access_controller.py"
    spec = importlib.util.spec_from_file_location("serial_access_controller_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SerialAccessControllerTest(unittest.TestCase):
    def setUp(self):
        self.module = load_controller_module()
        self.server_patch = patch.object(self.module, "SerialAccessServer", FakeServer)
        self.client_patch = patch.object(self.module, "SerialAccessClient", FakeClient)
        self.server_patch.start()
        self.client_patch.start()
        self.addCleanup(self.server_patch.stop)
        self.addCleanup(self.client_patch.stop)
        self.window = FakeMainWindow()
        self.controller = self.module.SerialAccessController(self.window)

    def test_start_server_creates_server_and_publishes_local_ports(self):
        self.window.app_config.serial_access_enabled = True

        self.controller.start_server()

        self.assertTrue(self.window._network_server.started)
        self.assertEqual(self.window._network_server.ports, ["COM1"])
        self.assertIs(self.window._serial_access_server, self.window._network_server)

    def test_start_client_connects_to_configured_address(self):
        self.controller.start_client()

        self.assertTrue(self.window._network_client.started)
        self.assertEqual(self.window._network_client.host, "127.0.0.1")
        self.assertEqual(self.window._network_client.port, 56338)
        self.assertEqual(self.window._network_client.access_password, "client-secret")

    def test_settings_only_configures_server_mode(self):
        settings = types.SimpleNamespace(
            host="127.0.0.1",
            port=56339,
            access_enabled=True,
            access_password="pw",
            max_clients=8,
            default_permission="read-only",
        )
        self.module.SerialAccessSettingsDialog.next_settings = settings

        self.controller.show_settings()

        self.assertEqual(self.window.app_config.serial_access_mode, "server")
        self.assertEqual(self.window.app_config.serial_access_host, "127.0.0.1")
        self.assertEqual(self.window.app_config.serial_access_port, 56339)
        self.assertEqual(self.window.app_config.serial_access_password, "pw")
        self.assertEqual(self.window.app_config.serial_access_client_password, "client-secret")
        self.assertEqual(self.window.app_config.serial_access_max_clients, 8)
        self.assertEqual(self.window.app_config.serial_access_default_permission, "read-only")
        self.assertTrue(self.window.config_manager.saved)

    def test_remote_dialog_starts_client_connection(self):
        settings = types.SimpleNamespace(
            server_address="10.0.0.5:56340",
            access_password="remote-pw",
        )
        self.module.RemoteSerialDialog.next_settings = settings

        self.controller.show_remote_connection()

        self.assertEqual(self.window.app_config.serial_access_server_address, "10.0.0.5:56340")
        self.assertEqual(self.window.app_config.serial_access_password, "secret")
        self.assertEqual(self.window.app_config.serial_access_client_password, "remote-pw")
        self.assertTrue(self.window._network_client.started)
        self.assertEqual(self.window._network_client.host, "10.0.0.5")
        self.assertEqual(self.window._network_client.port, 56340)

    def test_remote_dialog_keeps_existing_server_running(self):
        self.controller.start_server()
        server = self.window._network_server
        settings = types.SimpleNamespace(
            server_address="0.0.0.0:56338",
            access_password="secret",
        )
        self.module.RemoteSerialDialog.next_settings = settings

        self.controller.show_remote_connection()

        self.assertIs(self.window._network_server, server)
        self.assertFalse(server.stopped)
        self.assertTrue(self.window._network_client.started)
        self.assertEqual(self.window._network_client.host, "127.0.0.1")

    def test_remote_dialog_reconnects_when_same_server_client_is_disconnected(self):
        self.controller.start_client()
        old_client = self.window._network_client
        old_client.is_connected = False
        settings = types.SimpleNamespace(
            server_address="127.0.0.1:56338",
            access_password="secret",
        )
        self.module.RemoteSerialDialog.next_settings = settings

        self.controller.show_remote_connection()

        self.assertTrue(old_client.disconnected_called)
        self.assertIsNot(self.window._network_client, old_client)
        self.assertTrue(self.window._network_client.started)
        self.assertTrue(self.window._remote_serial_sessions.selection_requested)

    def test_stop_network_disconnects_and_closes_remote_sessions(self):
        self.controller.start_server()
        self.controller.start_client()

        client = self.window._network_client
        server = self.window._network_server
        self.controller.stop_network()

        self.assertTrue(client.disconnected_called)
        self.assertTrue(server.stopped)
        self.assertTrue(self.window._remote_serial_sessions.closed)
        self.assertIsNone(self.window._network_client)
        self.assertIsNone(self.window._network_server)


if __name__ == "__main__":
    unittest.main()
