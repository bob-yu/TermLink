import sys
import types
import unittest
import importlib.util
from pathlib import Path


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeAction:
    def __init__(self, text, parent=None):
        self._text = text
        self._shortcut = ""
        self._icon = None
        self._tooltip = ""
        self._status_tip = ""
        self.triggered = FakeSignal()

    def text(self):
        return self._text

    def setShortcut(self, shortcut):
        self._shortcut = shortcut

    def shortcut(self):
        return self._shortcut

    def setIcon(self, icon):
        self._icon = icon

    def icon(self):
        return self._icon

    def setToolTip(self, tooltip):
        self._tooltip = tooltip

    def toolTip(self):
        return self._tooltip

    def setStatusTip(self, status_tip):
        self._status_tip = status_tip

    def statusTip(self):
        return self._status_tip


if "PyQt5" not in sys.modules:
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
if "PyQt5.QtWidgets" not in sys.modules:
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    sys.modules["PyQt5.QtWidgets"] = qtwidgets
sys.modules["PyQt5.QtWidgets"].QAction = FakeAction

_actions_path = Path(__file__).resolve().parents[1] / "ui" / "actions.py"
_spec = importlib.util.spec_from_file_location("ui_actions_under_test", _actions_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
MainWindowActions = _module.MainWindowActions


class FakeController:
    def show(self):
        pass


class FakeWindow:
    def __init__(self):
        self._remote_log_download = FakeController()
        self._scan_pattern_settings = FakeController()
        self._terminal_settings = FakeController()
        self.access_control_opened = False

    def _scan_and_connect_all(self): pass
    def _add_serial_port(self): pass
    def _connect_all(self): pass
    def _disconnect_all(self): pass
    def _save_config(self): pass
    def close(self): pass
    def _add_ssh_connection(self): pass
    def _add_telnet_connection(self): pass
    def _add_raw_tcp_connection(self): pass
    def _add_remote_serial_connection(self): pass
    def _show_serial_remote_access_control(self):
        self.access_control_opened = True
    def _set_network_config(self): pass
    def _show_changelog(self): pass
    def _open_documentation(self): pass
    def _show_about(self): pass


class MainWindowActionsTest(unittest.TestCase):
    def test_core_action_labels_and_shortcuts(self):
        actions = MainWindowActions(FakeWindow())

        self.assertEqual(actions.scan_ports.text(), "Scan Ports")
        self.assertEqual(actions.scan_ports.shortcut(), "Ctrl+R")
        self.assertEqual(actions.add_serial.text(), "Serial")
        self.assertEqual(actions.add_serial.shortcut(), "Ctrl+N")
        self.assertEqual(actions.add_raw_tcp.text(), "Raw TCP")
        self.assertEqual(actions.access_settings.text(), "Serial Remote Access Settings")
        self.assertEqual(actions.access_control.text(), "Serial Remote Access Control")
        self.assertEqual(actions.open_docs.shortcut(), "F1")
        self.assertEqual(actions.open_docs.toolTip(), "Documentation (F1)")
        self.assertEqual(actions.access_settings.statusTip(), "Serial Remote Access Settings")
        self.assertEqual(actions.access_control.statusTip(), "Serial Remote Access Control")


if __name__ == "__main__":
    unittest.main()
