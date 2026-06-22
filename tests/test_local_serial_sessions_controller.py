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


class FakeSerialConfig:
    def __init__(self, port, baudrate, bytesize=8, parity="N", stopbits=1.0, flow_control="none", name=""):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.flow_control = flow_control
        self.name = name


class FakeWorker:
    def __init__(self, serial_config, *_args, **_kwargs):
        self.serial_config = serial_config
        self.data_received = FakeSignal()
        self.device_state_changed = FakeSignal()
        self.login_state_changed = FakeSignal()
        self.login_config = None
        self.commands = None
        self.keywords = None
        self.reconnect = None

    def setup_login(self, config):
        self.login_config = config

    def set_auto_commands(self, commands):
        self.commands = commands

    def set_keywords(self, keywords):
        self.keywords = keywords

    def set_auto_reconnect(self, enabled, interval):
        self.reconnect = (enabled, interval)


class FakeTab:
    def __init__(self, worker, scrollback, *args, **kwargs):
        self.worker = worker
        self.scrollback = scrollback
        self.font_family = kwargs.get("font_family", "")
        self.font_size = kwargs.get("font_size", 11)
        self.device_info_updated = FakeSignal()


class FakeTabWidget:
    def __init__(self):
        self.tabs = []
        self.tooltips = {}
        self.current = None

    def addTab(self, tab, name):
        self.tabs.append((tab, name))
        return len(self.tabs) - 1

    def setCurrentIndex(self, index):
        self.current = index

    def setTabToolTip(self, index, tooltip):
        self.tooltips[index] = tooltip


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class FakeLoginData:
    username = "root"
    password = "root"
    login_prompt = "login:"
    password_prompt = "Password:"
    shell_prompt = ["#"]


class FakePortConfig:
    port = "COM1"
    baudrate = 115200
    data_bits = 7
    parity = "E"
    stop_bits = 2.0
    flow_control = "rtscts"
    name = "DUT"
    login = FakeLoginData()
    auto_commands = ["echo ok"]
    keywords = {"error": ["error"]}


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
    def __init__(self, network_mode):
        self.app_config = FakeAppConfig()
        self._sessions = {}
        self._log_manager = object()
        self._network_mode = network_mode
        self.tab_widget = FakeTabWidget()
        self.statusbar = FakeStatusBar()
        self.server_ports_updated = 0
        self.refreshed = 0

    def _broadcast_serial_data(self, *_args): pass
    def _on_worker_device_state_changed(self, *_args): pass
    def _on_server_login_state_changed(self, *_args): pass
    def _parse_ip_from_data(self, *_args): pass
    def _on_device_info_updated(self, *_args): pass

    def _update_server_port_list(self):
        self.server_ports_updated += 1

    def _refresh_connection_panel(self):
        self.refreshed += 1


def load_controller_module():
    pyqt5 = types.ModuleType("PyQt5")
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    qtcore = types.ModuleType("PyQt5.QtCore")

    class QMessageBox:
        warnings = []

        @staticmethod
        def warning(parent, title, message):
            QMessageBox.warnings.append((parent, title, message))

    qtwidgets.QMessageBox = QMessageBox
    qtcore.QObject = object
    qtcore.pyqtSignal = lambda *args, **kwargs: FakeSignal()
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtWidgets"] = qtwidgets
    sys.modules["PyQt5.QtCore"] = qtcore

    serial_worker = types.ModuleType("core.serial_worker")
    serial_worker.SerialConfig = FakeSerialConfig
    serial_worker.SerialWorker = FakeWorker
    sys.modules["core.serial_worker"] = serial_worker

    ui_module = types.ModuleType("ui")
    ui_module.__path__ = []
    serial_tab = types.ModuleType("ui.serial_tab")
    serial_tab.SerialTab = FakeTab
    sys.modules["ui"] = ui_module
    sys.modules["ui.serial_tab"] = serial_tab

    path = Path(__file__).resolve().parents[1] / "ui" / "controllers" / "local_serial_sessions.py"
    spec = importlib.util.spec_from_file_location("local_serial_sessions_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalSerialSessionControllerTest(unittest.TestCase):
    def setUp(self):
        self.module = load_controller_module()

    def test_creates_local_serial_session(self):
        window = FakeMainWindow(self.module.SerialAccessMode.DISABLED)
        controller = self.module.LocalSerialSessionController(window)
        port_config = FakePortConfig()

        controller.create_session(port_config)

        self.assertIn("COM1", window._sessions)
        worker, _tab, config = window._sessions["COM1"]
        self.assertIs(config, port_config)
        self.assertEqual(worker.serial_config.port, "COM1")
        self.assertEqual(worker.serial_config.bytesize, 7)
        self.assertEqual(worker.serial_config.parity, "E")
        self.assertEqual(worker.serial_config.stopbits, 2.0)
        self.assertEqual(worker.serial_config.flow_control, "rtscts")
        self.assertEqual(worker.reconnect, (True, 5))
        self.assertEqual(_tab.font_family, "Consolas")
        self.assertEqual(_tab.font_size, 12)
        self.assertEqual(window.tab_widget.tabs[0][1], "DUT")
        self.assertEqual(window.server_ports_updated, 1)

    def test_server_mode_connects_extra_state_signals(self):
        window = FakeMainWindow(self.module.SerialAccessMode.SERVER)
        controller = self.module.LocalSerialSessionController(window)

        controller.create_session(FakePortConfig())

        worker, _tab, _config = window._sessions["COM1"]
        self.assertEqual(len(worker.login_state_changed.callbacks), 1)
        self.assertEqual(len(worker.data_received.callbacks), 2)


if __name__ == "__main__":
    unittest.main()
