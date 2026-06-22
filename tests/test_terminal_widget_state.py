import unittest

from PyQt5.QtWidgets import QApplication

from ui.terminal_widget import TerminalView


_APP = None


def ensure_app():
    global _APP
    _APP = QApplication.instance()
    if _APP is None:
        _APP = QApplication([])
    return _APP


class TerminalWidgetStateTest(unittest.TestCase):
    def test_sysrq_mode_is_initialized(self):
        ensure_app()
        view = TerminalView(lambda _data: None)
        try:
            self.assertFalse(view._sysrq_mode)
        finally:
            view.cleanup()

    def test_parent_lookup_finds_ancestor_capability(self):
        class Parent:
            def show_search_dialog(self, _selected_text):
                pass

            def parent(self):
                return None

        class Child:
            def __init__(self, parent=None):
                self._parent = parent

            def parent(self):
                return self._parent

        parent = Parent()
        child = Child(parent)
        view = Child(child)

        self.assertIs(TerminalView._find_parent_with(view, "show_search_dialog"), parent)
        self.assertIsNone(TerminalView._find_parent_with(view, "missing_capability"))


if __name__ == "__main__":
    unittest.main()
