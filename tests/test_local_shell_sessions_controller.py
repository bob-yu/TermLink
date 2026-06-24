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


class FakeConfig:
    def __init__(self, command="bash", name="Shell"):
        self.command = command
        self.name = name


class FakeWorker:
    def __init__(self, config, *_args, **_kwargs):
        self.config = config
        self.started = False
        self.state_changed = FakeSignal()

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
    scrollback_lines = 1000
    terminal_font_family = "Consolas"
    terminal_font_size = 12
    highlight_rules = []


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

    worker_module = types.ModuleType("core.local_shell_worker")
    worker_module.LocalShellConfig = FakeConfig
    worker_module.LocalShellWorker = FakeWorker
    worker_module.shell_display_name = lambda command: command
    sys.modules["core.local_shell_worker"] = worker_module

    ui_module = types.ModuleType("ui")
    ui_module.__path__ = []
    serial_tab = types.ModuleType("ui.serial_tab")
    serial_tab.SerialTab = FakeTab
    sys.modules["ui"] = ui_module
    sys.modules["ui.serial_tab"] = serial_tab

    path = Path(__file__).resolve().parents[1] / "ui" / "controllers" / "local_shell_sessions.py"
    spec = importlib.util.spec_from_file_location("local_shell_sessions_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalShellSessionControllerTest(unittest.TestCase):
    def test_creates_local_shell_session(self):
        module = load_controller_module()
        window = FakeMainWindow()
        controller = module.LocalShellSessionController(window)

        controller.create_session(FakeConfig(command="bash", name="Shell"))

        self.assertIn("localshell://Shell@bash", window._sessions)
        worker, _tab, config = window._sessions["localshell://Shell@bash"]
        self.assertIsInstance(config, FakeConfig)
        self.assertTrue(worker.started)
        self.assertEqual(window.tab_widget.tabs[0][1], "Shell")


if __name__ == "__main__":
    unittest.main()
