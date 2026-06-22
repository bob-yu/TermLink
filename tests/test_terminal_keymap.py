import importlib.util
from pathlib import Path
import unittest


def load_terminal_keymap():
    path = Path(__file__).resolve().parents[1] / "ui" / "terminal_keymap.py"
    spec = importlib.util.spec_from_file_location("terminal_keymap_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeQt:
    Key_A = 65
    Key_C = 67
    Key_D = 68
    Key_L = 76
    Key_Z = 90
    Key_Return = 1001
    Key_Enter = 1002
    Key_Backspace = 1003
    Key_Delete = 1004
    Key_Escape = 1005
    Key_Tab = 1006
    Key_Up = 1007
    Key_Down = 1008
    Key_Right = 1009
    Key_Left = 1010
    Key_Home = 1011
    Key_End = 1012
    Key_PageUp = 1013
    Key_PageDown = 1014
    Key_Insert = 1015
    Key_F1 = 1016
    Key_F2 = 1017
    Key_F3 = 1018
    Key_F4 = 1019
    Key_F5 = 1020
    Key_F6 = 1021
    Key_F7 = 1022
    Key_F8 = 1023
    Key_F9 = 1024
    Key_F10 = 1025
    Key_F11 = 1026
    Key_F12 = 1027


terminal_keymap = load_terminal_keymap()


class TerminalKeymapTest(unittest.TestCase):
    def test_control_sequence(self):
        self.assertEqual(terminal_keymap.control_sequence(FakeQt.Key_C, FakeQt), "\x03")
        self.assertEqual(terminal_keymap.control_sequence(FakeQt.Key_D, FakeQt), "\x04")
        self.assertEqual(terminal_keymap.control_sequence(FakeQt.Key_A, FakeQt), "\x01")

    def test_key_sequence_special_keys(self):
        self.assertEqual(terminal_keymap.key_sequence(FakeQt.Key_Return, "", FakeQt), "\r")
        self.assertEqual(terminal_keymap.key_sequence(FakeQt.Key_Up, "", FakeQt), "\x1b[A")
        self.assertEqual(terminal_keymap.key_sequence(FakeQt.Key_F5, "", FakeQt), "\x1b[15~")

    def test_key_sequence_text_fallback(self):
        self.assertEqual(terminal_keymap.key_sequence(9999, "x", FakeQt), "x")
        self.assertEqual(terminal_keymap.key_sequence(9999, "", FakeQt), "")


if __name__ == "__main__":
    unittest.main()
