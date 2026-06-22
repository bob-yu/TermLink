import unittest
import importlib.util
from pathlib import Path
import sys
import types


class FakeQColor:
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], str):
            self.value = args[0].lower()
        else:
            self.value = tuple(args)

    def isValid(self):
        return True

    def __eq__(self, other):
        return isinstance(other, FakeQColor) and self.value == other.value


qtgui = types.ModuleType("PyQt5.QtGui")
qtgui.QColor = FakeQColor
if "PyQt5" not in sys.modules:
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
sys.modules["PyQt5.QtGui"] = qtgui

_colors_path = Path(__file__).resolve().parents[1] / "ui" / "terminal_colors.py"
_spec = importlib.util.spec_from_file_location("terminal_colors_under_test", _colors_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
FG_COLOR = _module.FG_COLOR
terminal_color = _module.terminal_color


class TerminalColorTest(unittest.TestCase):
    def test_named_color(self):
        self.assertEqual(terminal_color("red", FG_COLOR), FakeQColor(205, 49, 49))

    def test_ansi_alias(self):
        self.assertEqual(terminal_color("ansibrightred", FG_COLOR), FakeQColor(241, 76, 76))

    def test_rgb_hex_from_pyte(self):
        self.assertEqual(terminal_color("010203", FG_COLOR), FakeQColor(1, 2, 3))

    def test_invalid_color_uses_default(self):
        self.assertEqual(terminal_color("not-a-color", FG_COLOR), FG_COLOR)


if __name__ == "__main__":
    unittest.main()
