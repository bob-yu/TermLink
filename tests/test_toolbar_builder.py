import importlib.util
import sys
import types
import unittest
from pathlib import Path


class FakeAction:
    def __init__(self, text=""):
        self._text = text
        self._visible = True
        self._icon = None
        self._tooltip = ""
        self._status_tip = ""

    def text(self):
        return self._text

    def setIcon(self, icon):
        self._icon = icon

    def setToolTip(self, tooltip):
        self._tooltip = tooltip

    def setStatusTip(self, status_tip):
        self._status_tip = status_tip

    def isVisible(self):
        return self._visible

    def setVisible(self, visible):
        self._visible = visible


class FakeMenu:
    def __init__(self, parent=None):
        self.parent = parent
        self.items = []

    def addAction(self, action):
        self.items.append(action)

    def addSeparator(self):
        self.items.append("separator")


class FakeToolButton:
    InstantPopup = 1

    def __init__(self, parent=None):
        self.parent = parent
        self.menu = None

    def setIcon(self, _icon): pass
    def setToolTip(self, _tooltip): pass
    def setStatusTip(self, _status_tip): pass
    def setPopupMode(self, _mode): pass
    def setAutoRaise(self, _enabled): pass

    def setMenu(self, menu):
        self.menu = menu


class FakeToolBar:
    def __init__(self, title):
        self.title = title
        self.items = []

    def setMovable(self, _enabled): pass
    def setToolButtonStyle(self, _style): pass
    def setIconSize(self, _size): pass
    def setStyleSheet(self, _style): pass

    def addAction(self, action):
        self.items.append(action)

    def addWidget(self, widget):
        self.items.append(widget)

    def addSeparator(self):
        self.items.append("separator")


class FakeQt:
    ToolButtonIconOnly = 1


class FakeSize:
    def __init__(self, width, height):
        self.width = width
        self.height = height


if "PyQt5" not in sys.modules:
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
qtcore = types.ModuleType("PyQt5.QtCore")
qtcore.Qt = FakeQt
qtcore.QSize = FakeSize
sys.modules["PyQt5.QtCore"] = qtcore
qtwidgets = types.ModuleType("PyQt5.QtWidgets")
qtwidgets.QMenu = FakeMenu
qtwidgets.QToolBar = FakeToolBar
qtwidgets.QToolButton = FakeToolButton
sys.modules["PyQt5.QtWidgets"] = qtwidgets

icon_provider = types.ModuleType("ui.icon_provider")
icon_provider.icon = lambda _name: object()
sys.modules["ui.icon_provider"] = icon_provider

module_path = Path(__file__).resolve().parents[1] / "ui" / "toolbar_builder.py"
spec = importlib.util.spec_from_file_location("ui.toolbar_builder", module_path)
module = importlib.util.module_from_spec(spec)
module.__package__ = "ui"
spec.loader.exec_module(module)


class FakeDock:
    def __init__(self, text):
        self.action = FakeAction(text)

    def toggleViewAction(self):
        return self.action


class FakeActions:
    def __init__(self):
        for name in [
            "scan_ports", "add_serial", "add_local_shell", "add_ssh", "add_telnet", "add_raw_tcp",
            "add_remote_serial", "connect_all", "disconnect_all",
            "access_settings", "access_control", "terminal_settings",
            "open_docs", "download_logs", "about", "exit_app",
        ]:
            setattr(self, name, FakeAction(name))


class FakeWindow:
    def __init__(self):
        self.actions = FakeActions()
        self.connection_panel = FakeDock("connections")
        self.runtime_log_panel = FakeDock("runtime log")
        self.command_set_panel = FakeDock("command sets")


class ToolbarBuilderTest(unittest.TestCase):
    def test_builds_core_toolbar_actions(self):
        toolbar = module.build_main_toolbar(FakeWindow())
        labels = [item.text() for item in toolbar.items if hasattr(item, "text")]

        self.assertIn("scan_ports", labels)
        self.assertIn("connect_all", labels)
        self.assertIn("disconnect_all", labels)
        self.assertIn("open_docs", labels)

        menus = [item.menu for item in toolbar.items if isinstance(item, FakeToolButton)]
        menu_labels = [
            action.text()
            for menu in menus
            for action in menu.items
            if hasattr(action, "text")
        ]
        self.assertIn("add_local_shell", menu_labels)
        self.assertIn("add_raw_tcp", menu_labels)
        self.assertIn("add_serial", menu_labels)
        self.assertIn("add_remote_serial", menu_labels)
        self.assertIn("terminal_settings", menu_labels)
        self.assertIn("about", menu_labels)


if __name__ == "__main__":
    unittest.main()
