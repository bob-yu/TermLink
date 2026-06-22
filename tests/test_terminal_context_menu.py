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


class FakeAction:
    def __init__(self, text, parent=None):
        self._text = text
        self._enabled = True
        self._shortcut = ""
        self.triggered = FakeSignal()

    def text(self):
        return self._text

    def setEnabled(self, enabled):
        self._enabled = enabled

    def isEnabled(self):
        return self._enabled

    def setShortcut(self, shortcut):
        self._shortcut = shortcut


class FakeMenu:
    def __init__(self, parent=None, title=""):
        self.title = title
        self.items = []

    def setStyleSheet(self, _style):
        pass

    def addAction(self, action):
        self.items.append(action)
        return action

    def addSeparator(self):
        self.items.append("---")

    def addMenu(self, title):
        menu = FakeMenu(title=title)
        self.items.append(menu)
        return menu


class FakeView:
    _has_selection = True
    _log_enabled = True

    def _copy_selection(self): pass
    def _paste_clipboard(self): pass
    def _select_all(self): pass
    def _show_search_dialog(self): pass
    def _show_watch_dialog(self): pass
    def _highlight_selection(self): pass
    def _show_highlight_rules(self): pass
    def _clear_highlight_rules(self): pass
    def scroll_to_bottom(self): pass
    def _connect_session(self): pass
    def _disconnect_session(self): pass
    def _send_break(self): pass
    def _clear_current_screen(self): pass
    def _clear_scrollback(self): pass
    def clear(self): pass
    def _toggle_log(self, _enabled): pass
    def _open_log_file(self): pass
    def _open_log_folder(self): pass
    def _show_terminal_settings(self): pass

    def _is_session_connected(self):
        return True


def load_module():
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    qtwidgets.QAction = FakeAction
    qtwidgets.QMenu = FakeMenu
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
    sys.modules["PyQt5.QtWidgets"] = qtwidgets

    path = Path(__file__).resolve().parents[1] / "ui" / "terminal_context_menu.py"
    spec = importlib.util.spec_from_file_location("terminal_context_menu_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TerminalContextMenuTest(unittest.TestCase):
    def test_menu_order(self):
        module = load_module()
        menu = module.build_terminal_context_menu(FakeView())

        labels = [
            item.title if isinstance(item, FakeMenu) else item.text() if item != "---" else "---"
            for item in menu.items
        ]

        self.assertEqual(labels[:11], [
            "Copy",
            "Paste",
            "Select All",
            "---",
            "Find...",
            "Watch...",
            "Highlight Selection",
            "Highlight Settings...",
            "Clear Highlights",
            "Scroll to Bottom",
            "---",
        ])
        self.assertIn("Clear", labels)
        self.assertIn("Log", labels)
        self.assertEqual(labels[-1], "Terminal Settings...")


if __name__ == "__main__":
    unittest.main()
