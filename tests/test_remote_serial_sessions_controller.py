import importlib.util
import sys
import types
import unittest
from pathlib import Path


if "PyQt5" not in sys.modules:
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
if "PyQt5.QtWidgets" not in sys.modules:
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    sys.modules["PyQt5.QtWidgets"] = qtwidgets

qtwidgets = sys.modules["PyQt5.QtWidgets"]
qtwidgets.QAbstractItemView = type("QAbstractItemView", (), {"ExtendedSelection": 1})
qtwidgets.QDialog = type("QDialog", (), {"Accepted": 1})
if "PyQt5.QtCore" not in sys.modules:
    qtcore = types.ModuleType("PyQt5.QtCore")
    sys.modules["PyQt5.QtCore"] = qtcore
sys.modules["PyQt5.QtCore"].Qt = type("Qt", (), {"UserRole": 32, "ItemIsEnabled": 1, "ItemIsSelectable": 2})
for name in ["QDialogButtonBox", "QListWidget", "QListWidgetItem", "QVBoxLayout"]:
    setattr(qtwidgets, name, type(name, (), {}))


class FakeDialog:
    selected = []
    last_opened_ports = []

    def __init__(self, ports, opened_ports=None, _parent=None):
        self.ports = ports
        self.opened_ports = opened_ports or []
        FakeDialog.last_opened_ports = self.opened_ports

    def exec_(self):
        return 1

    def selected_ports(self):
        return self.selected


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class FakeTabWidget:
    def __init__(self):
        self.tabs = []
        self.tooltips = {}

    def addTab(self, tab, name):
        self.tabs.append((tab, name))
        return len(self.tabs) - 1

    def count(self):
        return len(self.tabs)

    def widget(self, index):
        return self.tabs[index][0]

    def removeTab(self, index):
        self.tabs.pop(index)

    def setTabText(self, index, text):
        tab, _name = self.tabs[index]
        self.tabs[index] = (tab, text)

    def setTabToolTip(self, index, text):
        self.tooltips[index] = text


class FakeTerminal:
    def __init__(self):
        self.data = []

    def feed(self, data):
        self.data.append(data)


class FakeTab:
    def __init__(self, worker, _scrollback, *args, **kwargs):
        self.worker = worker
        self.terminal = FakeTerminal()
        self.closed = False
        self.font_family = kwargs.get("font_family", "")
        self.font_size = kwargs.get("font_size", 11)

    def close_session(self):
        self.closed = True


class FakeWorker:
    def __init__(self, client, remote_port):
        self.client = client
        self.remote_port = remote_port
        self.stopped = False
        self.started = False
        self._login_machine = None
        self._auto_login_enabled = False

    def setup_login(self, config):
        self.login_config = config

    def set_auto_commands(self, commands):
        self.commands = commands

    def set_keywords(self, keywords):
        self.keywords = keywords

    def stop(self):
        self.stopped = True

    def start(self):
        self.started = True
        if self.client and self.client.is_connected:
            self.client.select_port(self.remote_port)


class FakeConfig:
    scrollback_lines = 1000
    terminal_font_family = "Consolas"
    terminal_font_size = 12
    serial_access_server_address = "192.168.1.8:56337"


class FakeDefaultLogin:
    username = "root"
    password = "root"
    login_prompt = "login:"
    password_prompt = "Password:"
    shell_prompt = ["#"]


class FakeMainWindow:
    def __init__(self):
        self.statusbar = FakeStatusBar()
        self.tab_widget = FakeTabWidget()
        self.app_config = FakeConfig()
        self._sessions = {}
        self._network_client = FakeNetworkClient()
        self._remote_clients = FakeRemoteClients(self._network_client)
        self._serial_access_controller = FakeSerialAccessController(self)
        self._default_login = FakeDefaultLogin()
        self._default_auto_commands = ["echo ok"]
        self._default_keywords = {"error": ["error"]}
        self._remote_device_info_cache = {}
        self.refreshed = 0
        self.tooltips = []

    def _refresh_connection_panel(self):
        self.refreshed += 1

    def _update_tab_tooltip(self, tab, version, ip):
        self.tooltips.append((tab, version, ip))


class FakeNetworkClient:
    is_connected = True

    def __init__(self):
        self.selected_ports = []
        self.disconnected = False

    def select_port(self, port):
        self.selected_ports.append(port)

    def disconnect(self):
        self.disconnected = True
        self.is_connected = False


class FakeRemoteClients:
    def __init__(self, default_client):
        self._clients = {"": default_client}
        self.active_server_id = ""

    def get(self, server_id):
        return self._clients.get(server_id)

    def add(self, server_id, client):
        self._clients[server_id] = client
        self.active_server_id = server_id

    def remove(self, server_id, disconnect=True):
        client = self._clients.pop(server_id, None)
        if client and disconnect:
            client.disconnect()

    def server_ids(self):
        return list(self._clients.keys())


class FakeSerialAccessController:
    def __init__(self, window=None):
        self.window = window
        self.updated = 0

    def update_log_download_menu_visibility(self):
        self.updated += 1

    def remove_client(self, _server_id, disconnect=True):
        if self.window and hasattr(self.window, "_remote_clients"):
            self.window._remote_clients.remove(_server_id, disconnect=disconnect)
        if self.window and self.window._network_client and disconnect:
            self.window._network_client.disconnect()
            self.window._network_client = None
        self.updated += 1


def load_controller_module():
    qtwidgets = sys.modules["PyQt5.QtWidgets"]
    qtwidgets.QAbstractItemView = type("QAbstractItemView", (), {"ExtendedSelection": 1})
    qtwidgets.QDialog = type("QDialog", (), {"Accepted": 1})
    sys.modules["PyQt5.QtCore"].Qt = type("Qt", (), {"UserRole": 32, "ItemIsEnabled": 1, "ItemIsSelectable": 2})
    for name in ["QDialogButtonBox", "QListWidget", "QListWidgetItem", "QVBoxLayout"]:
        setattr(qtwidgets, name, type(name, (), {}))

    remote_worker = types.ModuleType("core.remote_worker")
    remote_worker.RemoteSerialWorkerProxy = FakeWorker
    serial_tab = types.ModuleType("ui.serial_tab")
    serial_tab.SerialTab = FakeTab
    sys.modules["core.remote_worker"] = remote_worker
    sys.modules["ui.serial_tab"] = serial_tab

    path = Path(__file__).resolve().parents[1] / "ui" / "controllers" / "remote_serial_sessions.py"
    spec = importlib.util.spec_from_file_location("remote_serial_sessions_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RemotePortSelectionDialog = FakeDialog
    return module


class RemoteSerialSessionControllerTest(unittest.TestCase):
    def setUp(self):
        self.module = load_controller_module()
        self.window = FakeMainWindow()
        self.controller = self.module.RemoteSerialSessionController(self.window)

    def test_creates_remote_session(self):
        self.controller.create_session("COM1")

        self.assertIn("remote://COM1", self.window._sessions)
        self.assertEqual(self.window.tab_widget.tabs[0][1], "192.168.1.8:COM1")
        self.assertEqual(self.window.refreshed, 1)
        worker, _tab, _config = self.window._sessions["remote://COM1"]
        self.assertTrue(worker.started)
        self.assertEqual(self.window._network_client.selected_ports, ["COM1"])

    def test_port_list_without_selection_does_not_auto_create_sessions(self):
        self.controller.on_port_list_received(["COM1", "COM2"])

        self.assertEqual(self.window._sessions, {})

    def test_port_list_selection_adds_selected_ports_only(self):
        FakeDialog.selected = ["COM2", "COM3"]
        self.controller.request_port_selection()

        self.controller.on_port_list_received(["COM1", "COM2", "COM3"])

        self.assertNotIn("remote://COM1", self.window._sessions)
        self.assertIn("remote://COM2", self.window._sessions)
        self.assertIn("remote://COM3", self.window._sessions)

    def test_cached_selection_marks_opened_ports(self):
        self.controller.create_session("COM1")
        self.controller.on_port_list_received(["COM1", "COM2"])
        FakeDialog.selected = ["COM2"]

        self.controller.show_cached_port_selection()

        self.assertEqual(FakeDialog.last_opened_ports, ["COM1"])
        self.assertIn("remote://COM1", self.window._sessions)
        self.assertIn("remote://COM2", self.window._sessions)

    def test_closed_remote_session_is_not_marked_opened(self):
        self.controller.create_session("COM1")
        worker, _tab, _config = self.window._sessions["remote://COM1"]
        client = self.window._network_client

        self.assertTrue(self.controller.close_session_for_worker(worker))
        FakeDialog.selected = ["COM1"]
        selected = self.controller._select_ports(["COM1", "COM2"])

        self.assertTrue(client.disconnected)
        self.assertIsNone(self.window._network_client)
        self.assertEqual(FakeDialog.last_opened_ports, [])
        self.assertEqual(selected, ["COM1"])

    def test_closing_one_of_multiple_remote_sessions_keeps_client_connected(self):
        self.controller.create_session("COM1")
        self.controller.create_session("COM2")
        worker, _tab, _config = self.window._sessions["remote://COM1"]
        client = self.window._network_client

        self.assertTrue(self.controller.close_session_for_worker(worker))

        self.assertFalse(client.disconnected)
        self.assertIs(self.window._network_client, client)
        self.assertIn("remote://COM2", self.window._sessions)

    def test_port_added_does_not_auto_create_session(self):
        self.controller.on_port_added("COM9")

        self.assertNotIn("remote://COM9", self.window._sessions)
        self.assertEqual(self.window.refreshed, 1)

    def test_removes_remote_session(self):
        self.controller.create_session("COM1")
        _worker, tab, _config = self.window._sessions["remote://COM1"]

        self.controller.on_port_removed("COM1")

        self.assertNotIn("remote://COM1", self.window._sessions)
        self.assertTrue(tab.closed)
        self.assertEqual(self.window.tab_widget.count(), 0)

    def test_forwards_remote_data_to_tab(self):
        self.controller.create_session("COM1")

        self.controller.on_data_received("COM1", "abc")

        _worker, tab, _config = self.window._sessions["remote://COM1"]
        self.assertEqual(tab.terminal.data, ["abc"])

    def test_same_remote_port_can_exist_on_different_servers(self):
        client_a = FakeNetworkClient()
        client_b = FakeNetworkClient()
        self.window._remote_clients.add("10.0.0.1:56337", client_a)
        self.window._remote_clients.add("10.0.0.2:56337", client_b)

        self.controller.create_session("COM1", "10.0.0.1:56337")
        self.controller.create_session("COM1", "10.0.0.2:56337")
        self.controller.on_data_received("COM1", "from-a", "10.0.0.1:56337")
        self.controller.on_data_received("COM1", "from-b", "10.0.0.2:56337")

        key_a = "remote://10.0.0.1:56337/COM1"
        key_b = "remote://10.0.0.2:56337/COM1"
        self.assertIn(key_a, self.window._sessions)
        self.assertIn(key_b, self.window._sessions)
        self.assertEqual(self.window._sessions[key_a][1].terminal.data, ["from-a"])
        self.assertEqual(self.window._sessions[key_b][1].terminal.data, ["from-b"])


if __name__ == "__main__":
    unittest.main()
