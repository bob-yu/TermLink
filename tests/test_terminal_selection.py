import importlib.util
from pathlib import Path
import unittest


def load_terminal_selection():
    path = Path(__file__).resolve().parents[1] / "ui" / "terminal_selection.py"
    spec = importlib.util.spec_from_file_location("terminal_selection_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


terminal_selection = load_terminal_selection()


class TerminalSelectionTest(unittest.TestCase):
    def test_word_char(self):
        self.assertTrue(terminal_selection.is_word_char("a"))
        self.assertTrue(terminal_selection.is_word_char("_"))
        self.assertFalse(terminal_selection.is_word_char(" "))

    def test_cell_selected_single_line(self):
        self.assertTrue(terminal_selection.is_cell_selected(1, 2, (1, 1), (1, 4)))
        self.assertFalse(terminal_selection.is_cell_selected(1, 4, (1, 1), (1, 4)))

    def test_cell_selected_reversed_multi_line(self):
        start = (3, 2)
        end = (1, 4)

        self.assertTrue(terminal_selection.is_cell_selected(1, 5, start, end))
        self.assertTrue(terminal_selection.is_cell_selected(2, 0, start, end))
        self.assertTrue(terminal_selection.is_cell_selected(3, 1, start, end))
        self.assertFalse(terminal_selection.is_cell_selected(3, 2, start, end))

    def test_selected_text_single_and_multi_line(self):
        lines = {0: "abcdef", 1: "ghijkl", 2: "mnopqr"}
        provider = lines.__getitem__

        self.assertEqual(terminal_selection.selected_text((0, 1), (0, 4), provider), "bcd")
        self.assertEqual(
            terminal_selection.selected_text((0, 2), (2, 3), provider),
            "cdef\nghijkl\nmno",
        )


if __name__ == "__main__":
    unittest.main()
