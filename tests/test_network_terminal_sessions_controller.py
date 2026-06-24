import importlib.util
import sys
import types
import unittest
from pathlib import Path


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeSSHConfig:
    def __init__(self, host="10.0.0.2", port=22, name=""):
        self.host = host
        self.port = port
        self.name = name


class FakeTelnetConfig:
    def __init__(self, host="10.0.0.3", port=23, name=""):
        self.host = host
        self.port = port
        self.name = name


class FakeRawTcpConfig:
    def __init__(self, host="10.0.0.4", port=2323, name=""):
        self.host = host
        self.port = port
        self.name = name


class FakeWorker:
    def __init__(self, config, *_args, **_kwargs):
        self.config = config
        self.reconnect = None
        self.started = False

    def set_auto_reconnect(self, enabled, interval):
        self.reconnect = (enabled, interval)

    def start(self):
        self.started = True


class FakeTab:
    def __init__(self, worker, scrollback, *args, **kwargs):
        self.worker = worker
        self.scrollback = scrollback
        self.font_family = kwargs.get("font_family", "")
        self.font_size = kwargs.get("font_size", 11)


class FakeTabWidget:
    def __init__(self):
        self.tabs = []
        self.current = None

    def addTab(self, tab, name):
        self.tabs.append((tab, name))
        return len(self.tabs) - 1

    def setCurrentIndex(self, index):
        self.current = index


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class FakeAppConfig:
    log_dir = "logs"
    log_enabled = True
    log_timestamp = True
    auto_reconnect = True
    reconnect_interval = 5
    scrollback_lines = 1000
    terminal_font_family = "Consolas"
    terminal_font_size = 12


class FakeMainWindow:
    def __init__(self):
        self.app_config = FakeAppConfig()
        self._sessions = {}
        self.tab_widget = FakeTabWidget()
        self.statusbar = FakeStatusBar()
        self.refreshed = 0

    def _refresh_connection_panel(self):
        self.refreshed += 1


def load_controller_module():
    pyqt5 = types.ModuleType("PyQt5")
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")

    class QMessageBox:
        warnings = []

        @staticmethod
        def warning(parent, title, message):
            QMessageBox.warnings.append((parent, title, message))

    qtwidgets.QMessageBox = QMessageBox
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtWidgets"] = qtwidgets

    ssh_worker = types.ModuleType("core.ssh_worker")
    ssh_worker.SSHConfig = FakeSSHConfig
    ssh_worker.RawTcpConfig = FakeRawTcpConfig
    ssh_worker.SSHWorker = FakeWorker
    ssh_worker.TelnetWorker = FakeWorker
    ssh_worker.RawTcpWorker = FakeWorker
    sys.modules["core.ssh_worker"] = ssh_worker

    ui_module = types.ModuleType("ui")
    ui_module.__path__ = []
    serial_tab = types.ModuleType("ui.serial_tab")
    serial_tab.SerialTab = FakeTab
    sys.modules["ui"] = ui_module
    sys.modules["ui.serial_tab"] = serial_tab

    path = Path(__file__).resolve().parents[1] / "ui" / "controllers" / "network_terminal_sessions.py"
    spec = importlib.util.spec_from_file_location("network_terminal_sessions_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NetworkTerminalSessionControllerTest(unittest.TestCase):
    def setUp(self):
        self.module = load_controller_module()
        self.window = FakeMainWindow()
        self.controller = self.module.NetworkTerminalSessionController(self.window)

    def test_creates_ssh_session(self):
        self.controller.create_session(FakeSSHConfig())

        self.assertIn("ssh://10.0.0.2:22", self.window._sessions)
        worker, _tab, config = self.window._sessions["ssh://10.0.0.2:22"]
        self.assertIsInstance(config, FakeSSHConfig)
        self.assertTrue(worker.started)
        self.assertEqual(worker.reconnect, (True, 5))
        self.assertEqual(self.window.tab_widget.tabs[0][1], "SSH:10.0.0.2")

    def test_creates_telnet_session(self):
        self.controller.create_session(FakeTelnetConfig())

        self.assertIn("telnet://10.0.0.3:23", self.window._sessions)
        self.assertEqual(self.window.tab_widget.tabs[0][1], "Telnet:10.0.0.3")

    def test_creates_raw_tcp_session(self):
        self.controller.create_session(FakeRawTcpConfig())

        self.assertIn("rawtcp://10.0.0.4:2323", self.window._sessions)
        self.assertEqual(self.window.tab_widget.tabs[0][1], "Raw TCP:10.0.0.4")


if __name__ == "__main__":
    unittest.main()
