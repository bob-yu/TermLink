import unittest
import importlib.util
from pathlib import Path


def load_terminal_search():
    path = Path(__file__).resolve().parents[1] / "ui" / "terminal_search.py"
    spec = importlib.util.spec_from_file_location("terminal_search_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


terminal_search = load_terminal_search()
find_matches = terminal_search.find_matches
initial_match_index = terminal_search.initial_match_index


class TerminalSearchTest(unittest.TestCase):
    def test_find_plain_text_case_insensitive_with_overlap(self):
        matches = find_matches([(0, "Banana")], "ana")

        self.assertEqual(matches, [(0, 1, 4), (0, 3, 6)])

    def test_find_plain_text_case_sensitive(self):
        lines = [(0, "Error error")]

        self.assertEqual(find_matches(lines, "error", case_sensitive=True), [(0, 6, 11)])
        self.assertEqual(
            find_matches(lines, "error", case_sensitive=False),
            [(0, 0, 5), (0, 6, 11)],
        )

    def test_find_regex(self):
        matches = find_matches([(2, "COM1 COM22")], r"COM\d+", regex=True)

        self.assertEqual(matches, [(2, 0, 4), (2, 5, 10)])

    def test_invalid_regex_returns_no_matches(self):
        self.assertEqual(find_matches([(0, "abc")], "(", regex=True), [])

    def test_initial_match_index(self):
        matches = [(0, 0, 1), (4, 0, 1), (9, 0, 1)]

        self.assertEqual(initial_match_index(matches, 5, direction_up=True), 1)
        self.assertEqual(initial_match_index(matches, -1, direction_up=True), 2)
        self.assertEqual(initial_match_index(matches, 5, direction_up=False), 0)
        self.assertEqual(initial_match_index([], 5, direction_up=True), -1)


if __name__ == "__main__":
    unittest.main()
